from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.state import AnalysisState
from backend.core.logging import get_logger
from backend.llm.context import build_context
from backend.llm.client import get_fast_llm
from backend.llm.utils import extract_json

logger = get_logger(__name__)

_FE_KEYWORDS   = {"component", "page", "view", "screen", "layout", "app", "store", "hook", "context", "redux", "router"}
_FE_EXTENSIONS = {".tsx", ".jsx", ".vue", ".svelte"}

SYSTEM_PROMPT = (
    "You are a senior frontend engineer. "
    "Respond ONLY with a single valid JSON object — no markdown fences, no explanation."
)

ANALYSIS_PROMPT = """Analyze the frontend code in this repository and return a JSON object with EXACTLY this schema:

{{
  "framework": "<React|Vue|Angular|Svelte|Next.js|Nuxt|None|unknown>",
  "state_management": "<Redux|Zustand|Pinia|Vuex|Context API|Jotai|None|unknown>",
  "routing": "<React Router|Next.js Router|Vue Router|TanStack Router|None|unknown>",
  "styling": "<Tailwind|CSS Modules|Styled Components|MUI|Chakra|None|unknown>",
  "component_count": <integer>,
  "key_components": [
    {{
      "name": "<component name>",
      "file": "<file path>",
      "purpose": "<what this component does>"
    }}
  ],
  "pages": [
    {{
      "name": "<page name>",
      "route": "<URL path>",
      "purpose": "<what this page shows>"
    }}
  ],
  "api_calls": ["<list of API endpoint paths this frontend calls>"]
}}

=== Frontend source files ===
{code_snippets}
"""


async def frontend_agent(state: AnalysisState) -> dict:
    llm     = get_fast_llm(temperature=0.1, max_tokens=1500)
    context = build_context(
        state.get("parsed_files", []),
        keywords=_FE_KEYWORDS,
        extensions=_FE_EXTENSIONS,
        max_files=10,
    )

    if not context:
        return {"frontend_report": None, "current_step": "frontend", "progress": 0.58}

    prompt = ANALYSIS_PROMPT.format(code_snippets=context)

    try:
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        data = extract_json(str(response.content))
    except Exception as exc:
        logger.warning("frontend_agent_error", error=str(exc))
        data = None

    logger.info("frontend_agent_complete")
    return {"frontend_report": data, "current_step": "frontend", "progress": 0.58}
