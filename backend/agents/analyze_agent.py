from __future__ import annotations

import asyncio

from backend.agents.architecture_agent import architecture_agent
from backend.agents.backend_agent import backend_agent
from backend.agents.database_agent import database_agent
from backend.agents.frontend_agent import frontend_agent
from backend.agents.security_agent import security_agent
from backend.agents.state import AnalysisState
from backend.core.logging import get_logger

logger = get_logger(__name__)

_AGENT_FUTS = [
    ("architecture", architecture_agent),
    ("backend",      backend_agent),
    ("frontend",     frontend_agent),
    ("database",     database_agent),
    ("security",     security_agent),
]

_MAX_RETRIES = 3
_RETRY_DELAYS = [2, 5, 10]  # seconds between attempts


async def analyze_agent(state: AnalysisState) -> dict:
    """
    Run sub-agents sequentially with per-agent retry and exponential backoff.
    Sequential execution avoids simultaneous rate-limit hits on Groq free tier.
    """
    logger.info("analyze_agent_start", agents=len(_AGENT_FUTS))

    merged: dict = {}
    errors: list[str] = []

    for name, fn in _AGENT_FUTS:
        result = None
        for attempt in range(_MAX_RETRIES):
            try:
                result = await fn(state)
                break
            except Exception as exc:
                err_str = str(exc)
                if attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        f"{name}_agent_retry",
                        attempt=attempt + 1,
                        delay=delay,
                        error=err_str[:120],
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"{name}_agent_failed", error=err_str[:200])
                    errors.append(f"{name}: {err_str[:120]}")

        if result is not None:
            for key, value in result.items():
                if key == "errors":
                    errors.extend(value if isinstance(value, list) else [value])
                elif key not in ("current_step", "progress"):
                    merged[key] = value

    if errors:
        merged["errors"] = errors

    merged["current_step"] = "analysis"
    merged["progress"]     = 0.75

    counts = {
        "arch":     bool(merged.get("architecture_report")),
        "backend":  len((merged.get("api_report") or {}).get("endpoints", [])),
        "frontend": bool(merged.get("frontend_report")),
        "database": len((merged.get("database_report") or {}).get("entities", [])),
        "security": len((merged.get("security_report") or {}).get("findings", [])),
    }
    logger.info("analyze_agent_complete", **counts)

    return merged
