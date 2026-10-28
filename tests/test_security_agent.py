import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_security_agent_success(sample_analysis_state):
    report = {
        "overall_risk": "medium",
        "summary": "The application has moderate security posture.",
        "authentication_analysis": "JWT-based auth is present.",
        "authorization_analysis": "Role-based access control.",
        "findings": [
            {
                "severity": "medium",
                "category": "Missing Rate Limiting",
                "description": "Login endpoint has no rate limiting.",
                "file_path": "api/auth.py",
                "line_number": 42,
                "recommendation": "Add slowapi rate limiting.",
            }
        ],
    }
    with patch("backend.agents.security_agent.get_fast_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(report)))
        mock_get_llm.return_value = mock_llm
        from backend.agents.security_agent import security_agent
        result = await security_agent(sample_analysis_state)

    assert result["security_report"]["overall_risk"] == "medium"
    assert len(result["security_report"]["findings"]) == 1
    assert result["progress"] == pytest.approx(0.73)


@pytest.mark.asyncio
async def test_security_agent_llm_error_fallback(sample_analysis_state):
    with patch("backend.agents.security_agent.get_fast_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("timeout"))
        mock_get_llm.return_value = mock_llm
        from backend.agents.security_agent import security_agent
        result = await security_agent(sample_analysis_state)

    assert result["security_report"]["overall_risk"] == "unknown"
    assert "findings" in result["security_report"]
