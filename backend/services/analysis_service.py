from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import AnalysisNotFoundError
from backend.core.logging import get_logger
from backend.models.db.analysis import Analysis
from backend.models.db.base import generate_uuid

logger = get_logger(__name__)


async def create_analysis(session: AsyncSession, repository_id: str) -> Analysis:
    analysis = Analysis(
        id=generate_uuid(),
        repository_id=repository_id,
        status="queued",
        progress=0.0,
    )
    session.add(analysis)
    await session.flush()
    logger.info("analysis_created", analysis_id=analysis.id, repo_id=repository_id)
    return analysis


async def get_analysis(session: AsyncSession, analysis_id: str) -> Analysis:
    analysis = await session.get(Analysis, analysis_id)
    if analysis is None:
        raise AnalysisNotFoundError(analysis_id)
    return analysis


async def get_latest_analysis_for_repo(
    session: AsyncSession, repository_id: str
) -> Analysis | None:
    result = await session.scalar(
        select(Analysis)
        .where(Analysis.repository_id == repository_id)
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    return result


async def list_analyses_for_repo(
    session: AsyncSession, repository_id: str
) -> list[Analysis]:
    result = await session.scalars(
        select(Analysis)
        .where(Analysis.repository_id == repository_id)
        .order_by(Analysis.created_at.desc())
    )
    return list(result.all())
