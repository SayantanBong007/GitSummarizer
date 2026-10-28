import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.models.db.base import Base
from backend.config import Settings

os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default asyncio policy. Provides session-scoped loop without deprecation."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content='{"style": "monolith", "description": "Test", "layers": [], "patterns": [], "strengths": [], "concerns": []}'))
    return llm


@pytest.fixture
def sample_parsed_file():
    return {
        "path": "src/main.py",
        "language": "python",
        "size_bytes": 1024,
        "symbols": [
            {
                "kind": "function",
                "name": "main",
                "start_line": 1,
                "end_line": 10,
                "docstring": "Entry point",
                "parent": None,
            },
            {
                "kind": "class",
                "name": "App",
                "start_line": 12,
                "end_line": 30,
                "docstring": None,
                "parent": None,
            },
        ],
        "imports": ["import os", "from pathlib import Path"],
        "raw_snippet": "import os\nfrom pathlib import Path\n\ndef main():\n    pass\n",
    }


@pytest.fixture
def sample_analysis_state(sample_parsed_file):
    return {
        "repo_url": "https://github.com/test/repo",
        "repo_id": "test-repo-id",
        "analysis_id": "test-analysis-id",
        "local_path": "/tmp/test-repo",
        "owner": "test",
        "repo_name": "repo",
        "default_branch": "main",
        "languages": ["python"],
        "frameworks": ["FastAPI"],
        "file_tree": {"src/main.py": {"size": 1024, "type": "file", "language": "python"}},
        "total_files": 1,
        "parsed_files": [sample_parsed_file],
        "tech_stack": {"backend": "FastAPI"},
        "knowledge_graph": {"nodes": [], "edges": []},
        "architecture_report": None,
        "module_breakdown": [],
        "design_patterns": [],
        "api_report": None,
        "frontend_report": None,
        "database_report": None,
        "security_report": None,
        "diagrams": {},
        "executive_summary": None,
        "markdown_docs": {},
        "current_step": "init",
        "progress": 0.0,
        "errors": [],
    }
