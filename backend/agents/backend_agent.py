from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.state import AnalysisState
from backend.core.logging import get_logger
from backend.llm.context import build_context
from backend.llm.client import get_fast_llm
from backend.llm.utils import extract_json

logger = get_logger(__name__)

_API_KEYWORDS   = {"route", "router", "controller", "endpoint", "handler", "api", "view", "rest", "graphql", "grpc", "middleware"}
_API_EXTENSIONS = {".py", ".ts", ".js", ".java", ".go", ".rb", ".php"}

SYSTEM_PROMPT = (
    "You are an expert backend engineer. "
    "Respond ONLY with a single valid JSON object — no markdown fences, no explanation."
)

ANALYSIS_PROMPT = """Analyze the backend/API layer of this repository and return a JSON object with EXACTLY this schema:

{{
  "type": "<REST|GraphQL|gRPC|WebSocket|mixed|none>",
  "base_path": "<API base URL prefix, e.g. /api/v1>",
  "authentication": "<JWT|OAuth2|Session|API Key|None|unknown>",
  "versioning": "<URL versioning|Header versioning|None|unknown>",
  "endpoints": [
    {{
      "method": "<GET|POST|PUT|DELETE|PATCH>",
      "path": "<endpoint path>",
      "summary": "<one-line description of what it does>",
      "auth_required": <true|false>,
      "tags": ["<category>"]
    }}
  ],
  "services": [
    {{
      "name": "<service class or module name>",
      "responsibility": "<single-sentence description>",
      "methods": ["<public method names>"]
    }}
  ]
}}

Languages: {languages}
Frameworks: {frameworks}

=== API / route / controller files ===
{code_snippets}
"""


async def backend_agent(state: AnalysisState) -> dict:
    llm     = get_fast_llm(temperature=0.1, max_tokens=1500)
    context = build_context(
        state.get("parsed_files", []),
        keywords=_API_KEYWORDS,
        extensions=_API_EXTENSIONS,
        max_files=10,
    )

    if not context:
        return {"api_report": {"type": "none", "endpoints": [], "services": []},
                "current_step": "backend", "progress": 0.50}

    prompt = ANALYSIS_PROMPT.format(
        languages=", ".join(state.get("languages", [])),
        frameworks=", ".join(state.get("frameworks", [])),
        code_snippets=context,
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        data = extract_json(str(response.content))
    except Exception as exc:
        logger.warning("backend_agent_error", error=str(exc))
        data = {"type": "unknown", "endpoints": [], "services": []}

    logger.info("backend_agent_complete", endpoints=len(data.get("endpoints", [])))
    return {"api_report": data, "current_step": "backend", "progress": 0.50}
