import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.repo_agent import (
    _build_file_tree,
    _detect_languages,
    _detect_frameworks,
    _ext_to_lang,
)


def test_ext_to_lang():
    assert _ext_to_lang(".py") == "python"
    assert _ext_to_lang(".ts") == "typescript"
    assert _ext_to_lang(".java") == "java"
    assert _ext_to_lang(".go") == "go"
    assert _ext_to_lang(".rs") == "rust"
    assert _ext_to_lang(".xyz") == "unknown"


def test_detect_languages():
    file_tree = {
        "a.py": {"language": "python"},
        "b.py": {"language": "python"},
        "c.ts": {"language": "typescript"},
        "d.go": {"language": "go"},
    }
    langs = _detect_languages(file_tree)
    assert langs[0] == "python"
    assert "typescript" in langs
    assert "go" in langs


def test_detect_languages_ignores_none():
    file_tree = {
        "README.md": {"language": None},
        "main.py": {"language": "python"},
    }
    langs = _detect_languages(file_tree)
    assert "python" in langs
    assert None not in langs


def test_detect_frameworks(tmp_path):
    (tmp_path / "angular.json").touch()
    frameworks = _detect_frameworks(tmp_path)
    assert "Angular" in frameworks


def test_detect_frameworks_docker(tmp_path):
    (tmp_path / "Dockerfile").touch()
    frameworks = _detect_frameworks(tmp_path)
    assert "Docker" in frameworks


@pytest.mark.asyncio
async def test_repo_agent_clone_failure(sample_analysis_state):
    from backend.core.exceptions import RepositoryCloneError
    from backend.agents.repo_agent import repo_agent

    with patch("git.Repo.clone_from", side_effect=Exception("Connection refused")):
        with pytest.raises(RepositoryCloneError):
            await repo_agent(sample_analysis_state)
