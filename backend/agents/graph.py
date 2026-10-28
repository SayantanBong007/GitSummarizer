"""
LangGraph orchestration graph — 5 top-level nodes, 9 logical analysis stages.

Flow:
  repo → parse → analyze (SEQUENTIAL sub-stages: arch, backend, frontend, db,
                 security -- deliberately not parallel, to avoid bursting
                 Groq's free-tier rate limit; see analyze_agent.py)
       → diagram → documentation
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.agents.analyze_agent import analyze_agent
from backend.agents.diagram_agent import diagram_agent
from backend.agents.documentation_agent import documentation_agent
from backend.agents.parsing_agent import parsing_agent
from backend.agents.repo_agent import repo_agent
from backend.agents.state import AnalysisState
from backend.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_STATE: AnalysisState = {
    "repo_url":           "",
    "repo_id":            "",
    "analysis_id":        "",
    "local_path":         "",
    "owner":              "",
    "repo_name":          "",
    "default_branch":     "main",
    "languages":          [],
    "frameworks":         [],
    "file_tree":          {},
    "total_files":        0,
    "parsed_files":       [],
    "tech_stack":         {},
    "knowledge_graph":    {"nodes": [], "edges": []},
    "architecture_report": None,
    "module_breakdown":   [],
    "design_patterns":    [],
    "api_report":         None,
    "frontend_report":    None,
    "database_report":    None,
    "security_report":    None,
    "diagrams":           {},
    "executive_summary":  None,
    "markdown_docs":      {},
    "current_step":       "init",
    "progress":           0.0,
    "errors":             [],
}


def _make_safe_node(agent_fn, agent_name: str):
    """Wrap an agent so that any uncaught exception is captured into state.errors."""
    async def _safe(state: AnalysisState) -> dict:
        try:
            return await agent_fn(state)
        except Exception as exc:
            logger.error(f"{agent_name}_failed", error=str(exc))
            return {"errors": [f"{agent_name}: {exc}"]}
    _safe.__name__ = agent_name
    return _safe


def build_graph() -> StateGraph:
    builder = StateGraph(AnalysisState)

    builder.add_node("repo",          _make_safe_node(repo_agent,          "repo_agent"))
    builder.add_node("parse",         _make_safe_node(parsing_agent,       "parsing_agent"))
    builder.add_node("analyze",       _make_safe_node(analyze_agent,       "analyze_agent"))
    builder.add_node("diagram",       _make_safe_node(diagram_agent,       "diagram_agent"))
    builder.add_node("documentation", _make_safe_node(documentation_agent, "documentation_agent"))

    builder.add_edge(START,          "repo")
    builder.add_edge("repo",         "parse")
    builder.add_edge("parse",        "analyze")
    builder.add_edge("analyze",      "diagram")
    builder.add_edge("diagram",      "documentation")
    builder.add_edge("documentation", END)

    return builder.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_analysis(
    repo_url: str,
    repo_id: str,
    analysis_id: str,
) -> AnalysisState:
    graph = get_graph()
    initial_state: AnalysisState = {
        **_DEFAULT_STATE,
        "repo_url":    repo_url,
        "repo_id":     repo_id,
        "analysis_id": analysis_id,
    }
    return await graph.ainvoke(initial_state)
