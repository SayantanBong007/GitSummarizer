from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.state import AnalysisState
from backend.core.logging import get_logger
from backend.llm.context import build_file_tree_summary, build_symbol_index
from backend.llm.router import TaskType, get_router
from backend.llm.utils import extract_json

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a senior software architect. "
    "Respond ONLY with a single valid JSON object — no markdown fences, no explanation."
)

ANALYSIS_PROMPT = """Analyze this repository's architecture and return a JSON object with EXACTLY this schema:

{{
  "style": "<monolith|modular_monolith|microservices|event_driven|hexagonal|clean_architecture|layered|cqrs|ddd>",
  "description": "<3-5 sentence explanation of the overall architecture>",
  "layers": [
    {{"name": "<layer name>", "description": "<what it does>", "path": "<folder pattern>"}}
  ],
  "patterns": ["<design pattern names detected, e.g. Repository, Factory, Observer>"],
  "strengths": ["<architectural strengths>"],
  "concerns": ["<architectural concerns or tech-debt>"],
  "module_breakdown": [
    {{
      "module": "<module/package name>",
      "responsibility": "<single-sentence description>",
      "public_interfaces": ["<key exported class or function names>"],
      "dependencies": ["<other modules it imports>"],
      "internal_flow": "<brief description of internal logic>"
    }}
  ]
}}

Repository: {owner}/{repo_name}
Primary languages: {languages}
Frameworks detected: {frameworks}
Total files: {total_files}

=== Full file tree ===
{file_tree}

=== Symbol index (path → classes / functions) ===
{symbol_index}
"""


async def architecture_agent(state: AnalysisState) -> dict:
    llm = get_router().get(TaskType.ANALYZE)

    file_tree    = build_file_tree_summary(state.get("file_tree", {}), max_entries=80)
    symbol_index = build_symbol_index(state.get("parsed_files", []), max_files=40)

    prompt = ANALYSIS_PROMPT.format(
        owner=state.get("owner", "unknown"),
        repo_name=state.get("repo_name", "unknown"),
        languages=", ".join(state.get("languages", [])),
        frameworks=", ".join(state.get("frameworks", [])),
        total_files=state.get("total_files", 0),
        file_tree=file_tree,
        symbol_index=symbol_index[:2_500],
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        data = extract_json(str(response.content))
        module_breakdown = data.pop("module_breakdown", [])
        patterns         = data.pop("patterns", [])
    except Exception as exc:
        logger.warning("architecture_agent_error", error=str(exc))
        data             = _fallback_architecture(state)
        module_breakdown = []
        patterns         = []

    logger.info("architecture_agent_complete", style=data.get("style"))
    return {
        "architecture_report": data,
        "module_breakdown":    module_breakdown,
        "design_patterns":     patterns,
        "current_step":        "architecture",
        "progress":            0.40,
    }


def _fallback_architecture(state: AnalysisState) -> dict:
    langs = ", ".join(state.get("languages", ["unknown"]))
    fws   = ", ".join(state.get("frameworks", []))
    return {
        "style":       "unknown",
        "description": f"Repository uses {langs}" + (f" with {fws}." if fws else "."),
        "layers":      [],
        "strengths":   [],
        "concerns":    ["Architecture could not be analyzed — LLM response was invalid."],
    }
