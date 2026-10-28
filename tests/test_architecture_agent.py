import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_architecture_agent_success(sample_analysis_state, mock_llm):
    expected = {
        "style": "clean_architecture",
        "description": "A layered FastAPI application.",
        "layers": [{"name": "API", "description": "HTTP layer", "path": "api/"}],
        "patterns": ["Repository", "Service Layer"],
        "strengths": ["Well separated concerns"],
        "concerns": [],
        "module_breakdown": [
            {
                "module": "auth",
                "responsibility": "Authentication",
                "public_interfaces": ["login", "logout"],
                "dependencies": ["database"],
                "internal_flow": "JWT-based",
            }
        ],
    }
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(expected)))

    with patch("backend.agents.architecture_agent.get_router") as mock_router:
        mock_router.return_value.get.return_value = mock_llm
        from backend.agents.architecture_agent import architecture_agent
        result = await architecture_agent(sample_analysis_state)

    assert result["architecture_report"]["style"] == "clean_architecture"
    assert "Repository" in result["design_patterns"]
    assert len(result["module_breakdown"]) == 1
    assert result["progress"] == pytest.approx(0.40)


@pytest.mark.asyncio
async def test_architecture_agent_fallback_on_llm_error(sample_analysis_state):
    with patch("backend.agents.architecture_agent.get_router") as mock_router:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))
        mock_router.return_value.get.return_value = mock_llm
        from backend.agents.architecture_agent import architecture_agent
        result = await architecture_agent(sample_analysis_state)

    assert result["architecture_report"] is not None
    assert result["architecture_report"]["style"] == "unknown"
