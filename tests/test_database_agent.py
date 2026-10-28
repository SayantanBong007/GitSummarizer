import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_database_agent_no_db_files(sample_analysis_state):
    with patch("backend.agents.database_agent.get_fast_llm") as mock_get_llm:
        mock_get_llm.return_value = AsyncMock()
        from backend.agents.database_agent import database_agent
        state = {**sample_analysis_state, "parsed_files": []}
        result = await database_agent(state)

    assert result["database_report"] is None
    assert result["progress"] == pytest.approx(0.65)


@pytest.mark.asyncio
async def test_database_agent_with_model_file(sample_analysis_state):
    db_file = {
        "path": "models/user.py",
        "language": "python",
        "size_bytes": 512,
        "symbols": [{"kind": "class", "name": "User", "start_line": 1, "end_line": 20, "docstring": None, "parent": None}],
        "imports": ["from sqlalchemy import Column, String"],
        "raw_snippet": "from sqlalchemy import Column, String\n\nclass User(Base):\n    id = Column(String)",
    }
    expected = {
        "orm": "SQLAlchemy",
        "database_type": "PostgreSQL",
        "migrations_present": False,
        "entities": [{"name": "User", "description": "User entity", "columns": [], "relationships": []}],
        "erd_mermaid": "erDiagram\nUser {\n}",
    }
    with patch("backend.agents.database_agent.get_fast_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(expected)))
        mock_get_llm.return_value = mock_llm
        from backend.agents.database_agent import database_agent
        state = {**sample_analysis_state, "parsed_files": [db_file]}
        result = await database_agent(state)

    assert result["database_report"]["orm"] == "SQLAlchemy"
    assert len(result["database_report"]["entities"]) == 1
