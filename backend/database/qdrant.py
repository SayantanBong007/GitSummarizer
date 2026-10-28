from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import Distance, VectorParams

from backend.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            check_compatibility=False,
        )
    return _client


async def close_qdrant_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def ensure_collection() -> None:
    settings = get_settings()
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection

    existing = {c.name for c in (await client.get_collections()).collections}
    if collection_name not in existing:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=20_000,
            ),
        )
        logger.info("qdrant_collection_created", collection=collection_name)
    else:
        logger.debug("qdrant_collection_exists", collection=collection_name)


async def upsert_points(
    points: list[models.PointStruct],
    collection_name: str | None = None,
) -> None:
    settings = get_settings()
    client = get_qdrant_client()
    name = collection_name or settings.qdrant_collection
    await client.upsert(collection_name=name, points=points, wait=True)


async def search_similar(
    vector: list[float],
    limit: int = 10,
    repo_id: str | None = None,
    collection_name: str | None = None,
) -> list[models.ScoredPoint]:
    settings = get_settings()
    client = get_qdrant_client()
    name = collection_name or settings.qdrant_collection

    query_filter: models.Filter | None = None
    if repo_id:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))]
        )

    result = await client.query_points(
        collection_name=name,
        query=vector,
        limit=limit,
        query_filter=query_filter,
        with_payload=True,
    )
    return result.points
