import pytest
from unittest.mock import AsyncMock, patch

from backend.knowledge_graph.builder import KnowledgeGraphBuilder


def test_build_from_parsed_files_creates_nodes():
    builder = KnowledgeGraphBuilder(repo_id="test-repo")
    parsed_files = [
        {
            "path": "src/main.py",
            "language": "python",
            "size_bytes": 512,
            "symbols": [
                {"kind": "function", "name": "run", "start_line": 1, "end_line": 5, "docstring": None, "parent": None},
                {"kind": "class", "name": "App", "start_line": 7, "end_line": 20, "docstring": None, "parent": None},
            ],
            "imports": [],
            "raw_snippet": "",
        }
    ]
    builder.build_from_parsed_files(parsed_files)
    state = builder.to_state_dict()

    node_types = {n["type"] for n in state["nodes"]}
    assert "File" in node_types
    assert "Function" in node_types
    assert "Class" in node_types

    node_names = {n["name"] for n in state["nodes"]}
    assert "run" in node_names
    assert "App" in node_names


def test_import_edge_created_for_relative_imports():
    builder = KnowledgeGraphBuilder(repo_id="test-repo")
    parsed_files = [
        {
            "path": "src/a.py",
            "language": "python",
            "size_bytes": 100,
            "symbols": [],
            "imports": ["from .b import helper"],
            "raw_snippet": "",
        },
        {
            "path": "src/b.py",
            "language": "python",
            "size_bytes": 100,
            "symbols": [],
            "imports": [],
            "raw_snippet": "",
        },
    ]
    builder.build_from_parsed_files(parsed_files)
    state = builder.to_state_dict()
    assert any(e["relationship"] == "IMPORTS" for e in state["edges"])


def test_defines_edges_created():
    builder = KnowledgeGraphBuilder(repo_id="test-repo")
    parsed_files = [
        {
            "path": "app.py",
            "language": "python",
            "size_bytes": 100,
            "symbols": [{"kind": "function", "name": "foo", "start_line": 1, "end_line": 3, "docstring": None, "parent": None}],
            "imports": [],
            "raw_snippet": "",
        }
    ]
    builder.build_from_parsed_files(parsed_files)
    state = builder.to_state_dict()
    assert any(e["relationship"] == "DEFINES" for e in state["edges"])


@pytest.mark.asyncio
async def test_persist_to_neo4j_called(sample_parsed_file):
    builder = KnowledgeGraphBuilder(repo_id="test-repo")
    builder.build_from_parsed_files([sample_parsed_file])

    with patch("backend.knowledge_graph.builder.run_query", new_callable=AsyncMock) as mock_q:
        await builder.persist_to_neo4j()
        assert mock_q.called
