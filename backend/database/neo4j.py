from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

from backend.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=50,
        )
    return _driver


@asynccontextmanager
async def get_neo4j_session() -> AsyncGenerator[AsyncSession, None]:
    driver = get_driver()
    async with driver.session() as session:
        yield session


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def run_query(
    cypher: str,
    params: dict[str, Any] | None = None,
    database: str = "neo4j",
) -> list[dict[str, Any]]:
    driver = get_driver()
    async with driver.session(database=database) as session:
        result = await session.run(cypher, parameters=params or {})
        records = await result.data()
        return records


async def ensure_constraints() -> None:
    """Create uniqueness constraints and indexes for the knowledge graph."""
    # Drop the old global path constraint — file paths are not globally unique
    # (two repos can both have backend/app.js). The id (md5 of repo_id+path) is unique.
    try:
        await run_query("DROP CONSTRAINT file_path IF EXISTS")
    except Exception:
        pass

    constraints = [
        # Uniqueness constraints (one per label)
        "CREATE CONSTRAINT file_id IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE",
        "CREATE CONSTRAINT function_id IF NOT EXISTS FOR (fn:Function) REQUIRE fn.id IS UNIQUE",
        "CREATE CONSTRAINT class_id IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT module_id IF NOT EXISTS FOR (m:Module) REQUIRE m.id IS UNIQUE",
        "CREATE CONSTRAINT endpoint_id IF NOT EXISTS FOR (e:APIEndpoint) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT table_id IF NOT EXISTS FOR (t:DBTable) REQUIRE t.id IS UNIQUE",
        # repo_id indexes — needed for GET_ALL_NODES / GET_ALL_RELATIONSHIPS filtering
        "CREATE INDEX file_repo IF NOT EXISTS FOR (f:File) ON (f.repo_id)",
        "CREATE INDEX function_repo IF NOT EXISTS FOR (fn:Function) ON (fn.repo_id)",
        "CREATE INDEX class_repo IF NOT EXISTS FOR (c:Class) ON (c.repo_id)",
        "CREATE INDEX endpoint_repo IF NOT EXISTS FOR (e:APIEndpoint) ON (e.repo_id)",
    ]
    for stmt in constraints:
        try:
            await run_query(stmt)
        except Exception as exc:
            logger.warning("neo4j_constraint_warning", stmt=stmt, error=str(exc))
