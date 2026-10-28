from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import RepositoryNotFoundError
from backend.core.logging import get_logger
from backend.models.db.base import generate_uuid
from backend.models.db.repository import Repository

logger = get_logger(__name__)


def _parse_github_url(url: str) -> tuple[str, str]:
    path = url.replace("https://github.com/", "").rstrip("/")
    parts = path.split("/")
    return parts[0], parts[1]


async def create_repository(session: AsyncSession, url: str) -> Repository:
    owner, name = _parse_github_url(url)

    existing = await session.scalar(
        select(Repository).where(Repository.url == url)
    )
    if existing:
        logger.info("repository_exists", url=url, repo_id=existing.id)
        return existing

    repo = Repository(
        id=generate_uuid(),
        url=url,
        owner=owner,
        name=name,
        clone_status="pending",
    )
    session.add(repo)
    await session.flush()
    logger.info("repository_created", url=url, repo_id=repo.id)
    return repo


async def get_repository(session: AsyncSession, repo_id: str) -> Repository:
    repo = await session.get(Repository, repo_id)
    if repo is None:
        raise RepositoryNotFoundError(repo_id)
    return repo


async def list_repositories(
    session: AsyncSession, offset: int = 0, limit: int = 20
) -> tuple[list[Repository], int]:
    total = await session.scalar(select(func.count()).select_from(Repository)) or 0
    result = await session.scalars(
        select(Repository).order_by(Repository.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.all()), total
