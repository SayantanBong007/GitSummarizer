from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.api.routes import analysis, chat, repositories
from backend.config import get_settings
from backend.core.exceptions import GitSummarizeError
from backend.core.limiter import limiter
from backend.core.logging import configure_logging, get_logger
from backend.database.neo4j import close_driver, ensure_constraints
from backend.database.postgres import close_engine
from backend.database.qdrant import close_qdrant_client, ensure_collection

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup_begin", env=settings.app_env)
    try:
        await ensure_constraints()
        logger.info("neo4j_ready")
    except Exception as exc:
        logger.warning("neo4j_unavailable", error=str(exc))

    try:
        await ensure_collection()
        logger.info("qdrant_ready")
    except Exception as exc:
        logger.warning("qdrant_unavailable", error=str(exc))

    logger.info("startup_complete")
    yield

    await close_engine()
    await close_driver()
    await close_qdrant_client()
    logger.info("shutdown_complete")


app = FastAPI(
    title="GitSummarize API",
    description="AI Repository Architect — automated architecture documentation",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(repositories.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


@app.exception_handler(GitSummarizeError)
async def domain_exception_handler(request: Request, exc: GitSummarizeError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
