import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from backend.main import app


@pytest.fixture
def mock_services():
    from backend.models.db.repository import Repository
    from backend.models.db.analysis import Analysis
    from datetime import datetime, timezone

    mock_repo = Repository(
        id="repo-123",
        url="https://github.com/test/repo",
        owner="test",
        name="repo",
        clone_status="cloned",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_analysis = Analysis(
        id="analysis-456",
        repository_id="repo-123",
        status="completed",
        progress=1.0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return mock_repo, mock_analysis


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_submit_repository_invalid_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/repositories/", json={"url": "not-a-github-url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_repository_success(mock_services, db_session):
    mock_repo, mock_analysis = mock_services

    with (
        patch("backend.api.routes.repositories.create_repository", return_value=mock_repo),
        patch("backend.api.routes.repositories.create_analysis", return_value=mock_analysis),
        patch("backend.api.routes.repositories.run_analysis_task") as mock_task,
        patch("backend.api.deps.get_session", return_value=db_session),
    ):
        mock_task.delay = MagicMock()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/repositories/",
                json={"url": "https://github.com/test/repo"}
            )

    assert response.status_code == 202
    data = response.json()
    assert "repository_id" in data
    assert "analysis_id" in data


@pytest.mark.asyncio
async def test_get_analysis_status_not_found():
    from backend.core.exceptions import AnalysisNotFoundError
    with patch("backend.api.routes.analysis.get_analysis", side_effect=AnalysisNotFoundError("nonexistent")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/analysis/nonexistent/status")
    assert response.status_code == 404
