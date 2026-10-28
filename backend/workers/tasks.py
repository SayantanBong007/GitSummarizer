from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime

import redis.asyncio as aioredis
from celery import Task
from sqlalchemy import update

from backend.config import get_settings
from backend.core.logging import get_logger
from backend.workers.celery_app import celery_app

logger = get_logger(__name__)


class AnalysisTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("analysis_task_failed", task_id=task_id, error=str(exc))


@celery_app.task(
    bind=True,
    base=AnalysisTask,
    name="backend.workers.tasks.run_analysis_task",
    max_retries=2,
    default_retry_delay=30,
)
def run_analysis_task(self, repo_url: str, repo_id: str, analysis_id: str) -> dict:
    # Synchronously drop the module-level asyncpg engine BEFORE asyncio.run() opens
    # a new event loop. Any engine created by a previous asyncio.run() is bound to
    # that (now-closed) loop; awaiting dispose() on it inside the new loop raises
    # "Future attached to a different loop". Resetting to None lets get_engine()
    # create a fresh engine inside the new loop.
    from backend.database.postgres import reset_engine
    reset_engine()
    return asyncio.run(_run_async(self, repo_url, repo_id, analysis_id))


def _make_headline(node_name: str, output: dict) -> str:
    """One-line summary of what this agent produced."""
    errors = output.get("errors", [])
    _output_keys = (
        "total_files", "parsed_files", "architecture_report",
        "api_report", "frontend_report", "database_report",
        "security_report", "diagrams", "executive_summary",
    )
    if errors and not any(output.get(k) for k in _output_keys):
        return f"Error: {errors[-1][:100]}"

    match node_name:
        case "repo":
            files = output.get("total_files", 0)
            langs = (output.get("languages") or [])[:3]
            lang_str = " · ".join(langs) if langs else "unknown"
            return f"{files:,} files · {lang_str}"
        case "parse":
            parsed = len(output.get("parsed_files") or [])
            stack = output.get("tech_stack") or {}
            frameworks = (stack.get("frameworks") or [])[:2]
            suffix = " · " + ", ".join(frameworks) if frameworks else ""
            return f"{parsed} files parsed{suffix}"
        case "analyze":
            arch     = (output.get("architecture_report") or {}).get("style", "?")
            endpoints = len((output.get("api_report") or {}).get("endpoints") or [])
            entities  = len((output.get("database_report") or {}).get("entities") or [])
            findings  = len((output.get("security_report") or {}).get("findings") or [])
            return f"{arch} · {endpoints} endpoints · {entities} entities · {findings} security findings"
        case "diagram":
            diagrams = output.get("diagrams") or {}
            count = len([v for v in diagrams.values() if v])
            return f"{count} diagram{'s' if count != 1 else ''} generated"
        case "documentation":
            docs = output.get("markdown_docs") or {}
            return f"{len(docs)} document{'s' if len(docs) != 1 else ''} written"
        case _:
            return ""


async def _run_async(task, repo_url: str, repo_id: str, analysis_id: str) -> dict:
    from backend.agents.graph import _DEFAULT_STATE, get_graph
    from backend.database.postgres import get_db_session
    from backend.models.db.analysis import Analysis
    from backend.models.db.repository import Repository

    settings = get_settings()
    redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
    channel = f"analysis:{analysis_id}"

    async def _publish(event: dict) -> None:
        await redis_client.publish(channel, json.dumps(event))

    async with get_db_session() as session:
        await session.execute(
            update(Analysis)
            .where(Analysis.id == analysis_id)
            .values(status="running", current_step="repo", step_log=[])
        )
        await session.execute(
            update(Repository)
            .where(Repository.id == repo_id)
            .values(clone_status="cloning")
        )

    initial_state: dict = {
        **_DEFAULT_STATE,
        "repo_url": repo_url,
        "repo_id": repo_id,
        "analysis_id": analysis_id,
    }
    final_state: dict = dict(initial_state)
    step_log: list[dict] = []
    step_start = time.monotonic()

    try:
        graph = get_graph()
        async for chunk in graph.astream(initial_state, stream_mode="updates"):
            node_name, node_output = next(iter(chunk.items()))
            duration = round(time.monotonic() - step_start, 1)
            step_start = time.monotonic()

            # Merge into final_state (handle errors reducer manually)
            for key, value in node_output.items():
                if key == "errors":
                    final_state["errors"] = final_state.get("errors", []) + value
                else:
                    final_state[key] = value

            event: dict = {
                "type": "step",
                "step": node_name,
                "progress": node_output.get("progress", final_state.get("progress", 0.0)),
                "current_step": node_output.get("current_step", node_name),
                "headline": _make_headline(node_name, node_output),
                "duration": duration,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            step_log.append(event)

            await _publish(event)
            async with get_db_session() as session:
                await session.execute(
                    update(Analysis)
                    .where(Analysis.id == analysis_id)
                    .values(
                        progress=event["progress"],
                        current_step=event["current_step"],
                        step_log=list(step_log),
                    )
                )

    except Exception as exc:
        async with get_db_session() as session:
            await session.execute(
                update(Analysis)
                .where(Analysis.id == analysis_id)
                .values(status="failed", error_message=str(exc)[:1000])
            )
        await _publish({"type": "error", "message": str(exc)[:500]})
        raise

    else:
        async with get_db_session() as session:
            await session.execute(
                update(Analysis)
                .where(Analysis.id == analysis_id)
                .values(
                    status="completed",
                    progress=1.0,
                    current_step="done",
                    step_log=list(step_log),
                    tech_stack=final_state.get("tech_stack"),
                    architecture_report=final_state.get("architecture_report"),
                    module_breakdown={"items": final_state.get("module_breakdown", [])},
                    api_report=final_state.get("api_report"),
                    database_report=final_state.get("database_report"),
                    frontend_report=final_state.get("frontend_report"),
                    security_report=final_state.get("security_report"),
                    design_patterns={"patterns": final_state.get("design_patterns", [])},
                    diagrams=final_state.get("diagrams"),
                    executive_summary=final_state.get("executive_summary"),
                    markdown_docs=final_state.get("markdown_docs"),
                )
            )
            await session.execute(
                update(Repository)
                .where(Repository.id == repo_id)
                .values(
                    clone_status="cloned",
                    local_path=final_state.get("local_path"),
                    languages=final_state.get("languages"),
                    frameworks=final_state.get("frameworks"),
                )
            )

        await _publish({"type": "done", "analysis_id": analysis_id})
        logger.info("analysis_task_complete", repo_id=repo_id, analysis_id=analysis_id)

    finally:
        # Always close the Redis connection regardless of success or failure
        await redis_client.aclose()

    return {"status": "completed", "analysis_id": analysis_id}

