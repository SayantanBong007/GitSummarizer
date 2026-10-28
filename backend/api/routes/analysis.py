from __future__ import annotations

import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_session
from backend.config import get_settings
from backend.core.exceptions import AnalysisNotFoundError, http_not_found
from backend.core.logging import get_logger
from backend.models.schemas.analysis import AnalysisResult, AnalysisStatus
from backend.services.analysis_service import get_analysis
from backend.services.export_service import export_to_json, export_to_markdown, export_to_pdf

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = get_logger(__name__)


@router.get("/{analysis_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(
    analysis_id: str,
    session: AsyncSession = Depends(get_session),
) -> AnalysisStatus:
    try:
        analysis = await get_analysis(session, analysis_id)
        return AnalysisStatus.model_validate(analysis)
    except AnalysisNotFoundError as exc:
        raise http_not_found(str(exc)) from exc


@router.get("/{analysis_id}/stream")
async def stream_analysis_events(
    analysis_id: str,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    SSE endpoint that streams analysis step events in real time.

    Event types:
      - step: an agent node completed  (data: StepEvent JSON)
      - done: analysis finished successfully
      - error: analysis failed
    """
    try:
        analysis = await get_analysis(session, analysis_id)
    except AnalysisNotFoundError as exc:
        raise http_not_found(str(exc)) from exc

    # Capture values before closing the session
    existing_step_log: list[dict] = list(analysis.step_log or [])
    terminal_status: str = analysis.status

    settings = get_settings()

    async def _generate():
        # 1. Replay historical steps already in the DB.
        #    Subscribe to Redis FIRST to avoid a race between replay and new events.
        redis_client = None
        pubsub = None
        try:
            redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(f"analysis:{analysis_id}")

            seen_steps: set[str] = set()
            for event in existing_step_log:
                step_id = event.get("step", "")
                seen_steps.add(step_id)
                yield f"event: step\ndata: {json.dumps(event)}\n\n"

            # 2. If already terminal, emit the final event and exit.
            if terminal_status == "completed":
                done_payload = json.dumps({"type": "done", "analysis_id": analysis_id})
                yield f"event: done\ndata: {done_payload}\n\n"
                return
            if terminal_status == "failed":
                yield f"event: error\ndata: {json.dumps({'type': 'error'})}\n\n"
                return

            # 3. Stream live events from Redis pub/sub.
            #    Use get_message() with a timeout so we can send heartbeats.
            heartbeat_interval = 15.0
            while True:
                try:
                    msg = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=None),
                        timeout=heartbeat_interval,
                    )
                except TimeoutError:
                    yield ": ping\n\n"
                    continue

                if msg is None:
                    await asyncio.sleep(0.05)
                    continue

                raw = msg.get("data", "")
                if not isinstance(raw, str):
                    continue

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                event_type = data.get("type", "step")

                # Skip steps already replayed from the DB snapshot
                if event_type == "step" and data.get("step") in seen_steps:
                    continue

                if event_type == "step":
                    seen_steps.add(data.get("step", ""))

                yield f"event: {event_type}\ndata: {raw}\n\n"

                if event_type in ("done", "error"):
                    break

        finally:
            if pubsub is not None:
                await pubsub.unsubscribe(f"analysis:{analysis_id}")
                await pubsub.aclose()
            if redis_client is not None:
                await redis_client.aclose()

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/{analysis_id}/result", response_model=AnalysisResult)
async def get_analysis_result(
    analysis_id: str,
    session: AsyncSession = Depends(get_session),
) -> AnalysisResult:
    try:
        analysis = await get_analysis(session, analysis_id)
    except AnalysisNotFoundError as exc:
        raise http_not_found(str(exc)) from exc

    from backend.models.schemas.analysis import (
        APIReport,
        ArchitectureReport,
        DatabaseReport,
        DiagramSet,
        SecurityReport,
        TechStackReport,
    )

    tech_stack = TechStackReport(**analysis.tech_stack) if analysis.tech_stack else None
    architecture = (
        ArchitectureReport(**analysis.architecture_report)
        if analysis.architecture_report
        else None
    )
    api_report = APIReport(**analysis.api_report) if analysis.api_report else None
    database_report = (
        DatabaseReport(**analysis.database_report) if analysis.database_report else None
    )
    security_report = (
        SecurityReport(**analysis.security_report) if analysis.security_report else None
    )
    diagrams = DiagramSet(**analysis.diagrams) if analysis.diagrams else None
    design_patterns = (
        analysis.design_patterns.get("patterns", []) if analysis.design_patterns else []
    )
    module_breakdown = (
        analysis.module_breakdown.get("items", []) if analysis.module_breakdown else []
    )

    return AnalysisResult(
        id=analysis.id,
        repository_id=analysis.repository_id,
        status=analysis.status,
        progress=analysis.progress,
        executive_summary=analysis.executive_summary,
        tech_stack=tech_stack,
        architecture=architecture,
        api_report=api_report,
        database_report=database_report,
        security_report=security_report,
        diagrams=diagrams,
        design_patterns=design_patterns,
        module_breakdown=module_breakdown,
        markdown_docs=analysis.markdown_docs or {},
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


@router.get("/{analysis_id}/export/json")
async def export_json(
    analysis_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        analysis = await get_analysis(session, analysis_id)
    except AnalysisNotFoundError as exc:
        raise http_not_found(str(exc)) from exc
    content = export_to_json(analysis)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="analysis_{analysis_id}.json"'},
    )


@router.get("/{analysis_id}/export/markdown")
async def export_markdown(
    analysis_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    try:
        analysis = await get_analysis(session, analysis_id)
    except AnalysisNotFoundError as exc:
        raise http_not_found(str(exc)) from exc
    return export_to_markdown(analysis)


@router.get("/{analysis_id}/export/pdf")
async def export_pdf(
    analysis_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    from fastapi import HTTPException, status as http_status

    try:
        analysis = await get_analysis(session, analysis_id)
    except AnalysisNotFoundError as exc:
        raise http_not_found(str(exc)) from exc
    try:
        pdf_bytes = await export_to_pdf(analysis)
    except RuntimeError as exc:
        logger.warning("pdf_export_failed", analysis_id=analysis_id, error=str(exc))
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF rendering unavailable in this environment. Use JSON export instead.",
        ) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{analysis_id}.pdf"'},
    )
