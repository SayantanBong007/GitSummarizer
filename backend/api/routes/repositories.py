from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_session
from backend.core.exceptions import RepositoryNotFoundError, http_not_found
from backend.core.limiter import limiter
from backend.core.logging import get_logger
from backend.database.neo4j import run_query
from backend.knowledge_graph import queries
from backend.models.schemas.analysis import AnalysisStatus
from backend.models.schemas.repository import (
    RepositoryListResponse,
    RepositoryResponse,
    RepositorySubmit,
)
from backend.services.analysis_service import create_analysis, get_latest_analysis_for_repo
from backend.services.repository_service import (
    create_repository,
    get_repository,
    list_repositories,
)
from backend.workers.tasks import run_analysis_task

router = APIRouter(prefix="/repositories", tags=["repositories"])
logger = get_logger(__name__)


@router.post("/", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/hour")
async def submit_repository(
    request: Request,
    body: RepositorySubmit,
    session: AsyncSession = Depends(get_session),
) -> dict:
    repo = await create_repository(session, body.url)
    analysis = await create_analysis(session, repo.id)
    await session.commit()

    run_analysis_task.delay(
        repo_url=repo.url,
        repo_id=repo.id,
        analysis_id=analysis.id,
    )

    logger.info("analysis_queued", repo_id=repo.id, analysis_id=analysis.id)
    return {
        "repository_id": repo.id,
        "analysis_id": analysis.id,
        "message": "Analysis queued successfully",
    }


@router.get("/", response_model=RepositoryListResponse)
async def list_repos(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> RepositoryListResponse:
    repos, total = await list_repositories(session, offset=offset, limit=limit)
    return RepositoryListResponse(
        items=[RepositoryResponse.model_validate(r) for r in repos],
        total=total,
    )


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repo(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> RepositoryResponse:
    try:
        repo = await get_repository(session, repo_id)
        return RepositoryResponse.model_validate(repo)
    except RepositoryNotFoundError as exc:
        raise http_not_found(str(exc)) from exc


@router.get("/{repo_id}/analysis", response_model=AnalysisStatus | None)
async def get_repo_analysis_status(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> AnalysisStatus | None:
    try:
        await get_repository(session, repo_id)
    except RepositoryNotFoundError as exc:
        raise http_not_found(str(exc)) from exc

    analysis = await get_latest_analysis_for_repo(session, repo_id)
    if analysis is None:
        return None
    return AnalysisStatus.model_validate(analysis)


@router.get("/{repo_id}/graph")
async def get_repo_graph(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return the real knowledge graph from Neo4j for this repository."""
    try:
        await get_repository(session, repo_id)
    except RepositoryNotFoundError as exc:
        raise http_not_found(str(exc)) from exc

    try:
        raw_nodes = await run_query(queries.GET_ALL_NODES, {"repo_id": repo_id})
        raw_edges = await run_query(queries.GET_ALL_RELATIONSHIPS, {"repo_id": repo_id})
    except Exception as exc:
        logger.warning("neo4j_graph_query_failed", repo_id=repo_id, error=str(exc))
        return {"nodes": [], "edges": []}

    nodes = [
        {
            "id":        r["id"],
            "type":      r["type"],
            "name":      r["name"] or r["id"],
            "file_path": r.get("file_path"),
        }
        for r in raw_nodes
        if r.get("id")
    ]
    edges = [
        {
            "source_id":    r["source"],
            "target_id":    r["target"],
            "relationship": r["relationship"],
        }
        for r in raw_edges
        if r.get("source") and r.get("target")
    ]

    logger.info("graph_served", repo_id=repo_id, nodes=len(nodes), edges=len(edges))
    return {"nodes": nodes, "edges": edges}


@router.post("/{repo_id}/reanalyze", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/hour")
async def reanalyze_repository(
    request: Request,
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete existing graph data and queue a fresh analysis for this repository."""
    try:
        repo = await get_repository(session, repo_id)
    except RepositoryNotFoundError as exc:
        raise http_not_found(str(exc)) from exc

    # Wipe old Neo4j nodes so the graph starts clean
    try:
        await run_query(queries.DELETE_REPO_GRAPH, {"repo_id": repo_id})
    except Exception as exc:
        logger.warning("neo4j_delete_failed", repo_id=repo_id, error=str(exc))

    analysis = await create_analysis(session, repo_id)
    await session.commit()

    run_analysis_task.delay(
        repo_url=repo.url,
        repo_id=repo_id,
        analysis_id=analysis.id,
    )

    logger.info("reanalysis_queued", repo_id=repo_id, analysis_id=analysis.id)
    return {
        "repository_id": repo_id,
        "analysis_id": analysis.id,
        "message": "Re-analysis queued successfully",
    }
