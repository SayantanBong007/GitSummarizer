from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

# ---------------------------------------------------------------------------
# Sub-types used within state
# ---------------------------------------------------------------------------

class ParsedSymbol(TypedDict):
    kind: str        # function | class | method | import | variable
    name: str
    start_line: int
    end_line: int
    docstring: str | None
    parent: str | None  # enclosing class name for methods


class ParsedFile(TypedDict):
    path: str
    language: str
    size_bytes: int
    symbols: list[ParsedSymbol]
    imports: list[str]
    raw_snippet: str  # first 200 lines for LLM context


class KnowledgeGraphData(TypedDict):
    nodes: list[dict]   # {id, type, name, file, ...}
    edges: list[dict]   # {source, target, relationship}


# ---------------------------------------------------------------------------
# Primary LangGraph state — accumulated across all agents
# ---------------------------------------------------------------------------

class AnalysisState(TypedDict):
    # Input
    repo_url: str
    repo_id: str
    analysis_id: str

    # Repo agent output
    local_path: str
    owner: str
    repo_name: str
    default_branch: str
    languages: list[str]
    frameworks: list[str]
    file_tree: dict        # {path: {size, type, language}}
    total_files: int

    # Parsing agent output
    parsed_files: list[ParsedFile]
    tech_stack: dict

    # Knowledge graph (built during parsing)
    knowledge_graph: KnowledgeGraphData

    # Architecture agent output
    architecture_report: dict | None
    module_breakdown: list[dict]
    design_patterns: list[str]

    # Backend agent output
    api_report: dict | None

    # Frontend agent output
    frontend_report: dict | None

    # Database agent output
    database_report: dict | None

    # Security agent output
    security_report: dict | None

    # Diagram agent output
    diagrams: dict  # {name: mermaid_code}

    # Documentation agent output
    executive_summary: str | None
    markdown_docs: dict  # {filename: content}

    # Pipeline control
    current_step: str
    progress: float
    errors: Annotated[list[str], add]  # accumulates across agents
