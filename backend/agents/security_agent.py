from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.state import AnalysisState
from backend.core.logging import get_logger
from backend.llm.context import build_context
from backend.llm.client import get_fast_llm
from backend.llm.utils import extract_json

logger = get_logger(__name__)

_SEC_KEYWORDS   = {"auth", "login", "password", "token", "secret", "key", "credential",
                   "jwt", "session", "permission", "role", "middleware", "cors", "config",
                   "env", "settings", "security", "encrypt", "hash", "sanitize", "validate"}
_SEC_EXTENSIONS = {".py", ".ts", ".js", ".java", ".go", ".env", ".yaml", ".yml"}

SYSTEM_PROMPT = (
    "You are an application security engineer (OWASP, SAST expert). "
    "Respond ONLY with a single valid JSON object — no markdown fences, no explanation."
)

ANALYSIS_PROMPT = """Perform a security review of this codebase and return a JSON object with EXACTLY this schema:

{{
  "overall_risk": "<critical|high|medium|low>",
  "summary": "<2-3 sentence security posture summary>",
  "authentication_analysis": "<explain the auth mechanism and any gaps>",
  "authorization_analysis": "<explain the authorization model>",
  "findings": [
    {{
      "severity": "<critical|high|medium|low|info>",
      "category": "<e.g. Hardcoded Secret|SQL Injection|Missing Auth|CORS Misconfiguration|XSS|SSRF|Insecure Dependency|etc>",
      "description": "<what the issue is and why it matters>",
      "file_path": "<file where found, or null>",
      "line_number": <integer line number or null>,
      "recommendation": "<specific actionable fix>"
    }}
  ]
}}

Languages: {languages}
Frameworks: {frameworks}

=== Security-relevant files (auth, config, middleware, env handling) ===
{code_snippets}
"""


async def security_agent(state: AnalysisState) -> dict:
    llm     = get_fast_llm(temperature=0.1, max_tokens=1500)
    context = build_context(
        state.get("parsed_files", []),
        keywords=_SEC_KEYWORDS,
        extensions=_SEC_EXTENSIONS,
        max_files=10,
    )

    if not context:
        return {
            "security_report": {"overall_risk": "unknown", "summary": "No files to analyze.", "findings": []},
            "current_step": "security",
            "progress": 0.73,
        }

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
        logger.warning("security_agent_error", error=str(exc))
        data = {"overall_risk": "unknown", "summary": "Security analysis failed.", "findings": []}

    logger.info("security_agent_complete", risk=data.get("overall_risk"),
                findings=len(data.get("findings", [])))
    return {"security_report": data, "current_step": "security", "progress": 0.73}
