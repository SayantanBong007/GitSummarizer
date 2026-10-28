from fastapi import APIRouter, Depends, HTTPException, Request, status
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_session
from backend.core.limiter import limiter
from backend.core.logging import get_logger
from backend.database.qdrant import search_similar
from backend.embeddings.pipeline import embed_query
from backend.llm.router import TaskType, get_router
from backend.models.schemas.analysis import ChatMessage, ChatRequest, ChatResponse
from backend.services.analysis_service import get_latest_analysis_for_repo

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)

CHAT_SYSTEM = (
    "You are an expert software architect answering questions about a specific code repository. "
    "Use the provided code context and analysis data to answer precisely. "
    "If the context doesn't contain the answer, say so. "
    "Be concise and technical."
)


def _build_analysis_context(analysis) -> str:
    """Convert stored analysis fields into a structured text block for the system prompt."""
    if analysis is None:
        return ""

    parts: list[str] = ["=== Repository Analysis ==="]

    # Tech stack
    ts = analysis.tech_stack or {}
    if ts:
        langs = ts.get("languages") or []
        fws   = ts.get("frameworks") or []
        parts.append(f"Languages: {', '.join(langs) if langs else 'unknown'}")
        if fws:
            parts.append(f"Frameworks: {', '.join(fws)}")

    # Architecture
    arch = analysis.architecture_report or {}
    if arch.get("style"):
        parts.append(f"Architecture: {arch['style']} — {arch.get('description', '')[:200]}")
    if arch.get("concerns"):
        concerns = arch["concerns"][:3]
        parts.append(f"Concerns: {'; '.join(concerns)}")

    # API
    api = analysis.api_report or {}
    endpoints = api.get("endpoints") or []
    if endpoints:
        ep_lines = [f"  {e.get('method','?')} {e.get('path','?')}" for e in endpoints[:12]]
        parts.append(f"API endpoints ({len(endpoints)} total):\n" + "\n".join(ep_lines))

    # Database
    db = analysis.database_report or {}
    entities = db.get("entities") or []
    if entities:
        names = [e.get("name", "?") for e in entities[:10]]
        parts.append(f"DB entities: {', '.join(names)}")
    if db.get("orm"):
        parts.append(f"ORM: {db['orm']}")

    # Security
    sec = analysis.security_report or {}
    if sec.get("overall_risk"):
        parts.append(f"Security risk: {sec['overall_risk'].upper()}")
    findings = sec.get("findings") or []
    if findings:
        top = findings[:4]
        finding_lines = [
            f"  [{f.get('severity','?').upper()}] {f.get('category','?')}: {f.get('description','')[:80]}"
            for f in top
        ]
        parts.append(f"Top security findings:\n" + "\n".join(finding_lines))

    # Module breakdown
    mb_raw = analysis.module_breakdown or {}
    modules = mb_raw.get("items") or []
    if modules:
        mod_lines = [
            f"  {m.get('module','?')}: {m.get('responsibility','')[:80]}"
            for m in modules[:8]
        ]
        parts.append("Module breakdown:\n" + "\n".join(mod_lines))

    # Executive summary (first 400 chars)
    if analysis.executive_summary:
        excerpt = analysis.executive_summary[:400].replace("\n", " ")
        parts.append(f"Executive summary: {excerpt}…")

    return "\n".join(parts)


@router.post("/", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_with_repo(
    request: Request,
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    user_message = body.messages[-1].content if body.messages else ""

    # Fetch analysis context and Qdrant code hits in parallel
    import asyncio
    query_vector = await embed_query(user_message)
    analysis, search_results = await asyncio.gather(
        get_latest_analysis_for_repo(session, body.repository_id),
        search_similar(vector=query_vector, limit=6, repo_id=body.repository_id),
    )

    # Build structured analysis context
    analysis_ctx = _build_analysis_context(analysis)

    # Build code snippet context from Qdrant
    context_parts: list[str] = []
    sources: list[dict] = []
    for hit in search_results:
        payload = hit.payload or {}
        context_parts.append(
            f"File: {payload.get('file_path', 'unknown')}\n"
            f"Symbol: {payload.get('symbol_name', '')}\n"
            f"```\n{payload.get('text', '')}\n```"
        )
        sources.append({
            "file":   payload.get("file_path"),
            "symbol": payload.get("symbol_name"),
            "score":  round(float(hit.score), 3),
        })

    code_ctx = "\n\n---\n\n".join(context_parts)

    system_content = CHAT_SYSTEM
    if analysis_ctx:
        system_content += f"\n\n{analysis_ctx}"
    if code_ctx:
        system_content += f"\n\n=== Relevant Code ===\n{code_ctx}"

    llm = get_router().get(TaskType.CHAT)

    # Limit history to 6 messages (3 Q&A pairs) to stay within 12k TPM
    recent_messages = body.messages[-6:]

    messages = [SystemMessage(content=system_content)]
    for msg in recent_messages:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))

    try:
        response = await llm.ainvoke(messages)
    except Exception as exc:
        logger.warning("chat_llm_failed", error=str(exc)[:200])
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM temporarily unavailable — all models are rate-limited. Try again in a moment.",
        ) from exc

    answer = str(response.content).strip()
    logger.info("chat_response", repo_id=body.repository_id, sources=len(sources))

    return ChatResponse(
        message=ChatMessage(role="assistant", content=answer),
        sources=sources,
    )
