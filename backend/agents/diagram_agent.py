from __future__ import annotations

import re
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.state import AnalysisState
from backend.core.logging import get_logger
from backend.llm.router import TaskType, get_router
from backend.llm.utils import extract_json

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a software architect who creates Mermaid diagrams.
Respond ONLY with valid JSON containing Mermaid diagram strings.
All mermaid code must be valid and renderable."""

DIAGRAM_PROMPT = """Generate Mermaid diagrams for this repository and return JSON:

{{
  "architecture": "<flowchart TD mermaid diagram showing system architecture>",
  "class_diagram": "<classDiagram mermaid showing key classes and relationships>",
  "sequence_flows": {{
    "<flow_name>": "<sequenceDiagram mermaid for this business flow>"
  }},
  "er_diagram": "<erDiagram mermaid if database entities exist, else null>",
  "dependency_graph": "<flowchart LR mermaid showing module dependencies>"
}}

Repository summary:
- Architecture style: {arch_style}
- Languages: {languages}
- Frameworks: {frameworks}
- API type: {api_type}
- DB entities: {db_entities}
- Key modules: {modules}
- Design patterns: {patterns}
"""


async def diagram_agent(state: AnalysisState) -> AnalysisState:
    llm = get_router().get(TaskType.GENERATE)

    arch = state.get("architecture_report") or {}
    api = state.get("api_report") or {}
    db = state.get("database_report") or {}

    db_entities = [e.get("name", "") for e in db.get("entities", [])][:10]
    modules = [m.get("module", "") for m in state.get("module_breakdown", [])][:8]

    prompt = DIAGRAM_PROMPT.format(
        arch_style=arch.get("style", "unknown"),
        languages=", ".join(state.get("languages", [])),
        frameworks=", ".join(state.get("frameworks", [])),
        api_type=api.get("type", "unknown"),
        db_entities=", ".join(db_entities) or "none detected",
        modules=", ".join(modules) or "none detected",
        patterns=", ".join(state.get("design_patterns", [])) or "none detected",
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        diagrams = extract_json(str(response.content))
        if not isinstance(diagrams, dict):
            raise ValueError("Expected dict")
    except Exception as exc:
        logger.warning("diagram_agent_error", error=str(exc))
        diagrams = _generate_fallback_diagrams(state)

    # Sanitize all string values to fix common LLM Mermaid syntax mistakes
    diagrams = _sanitize_diagrams(diagrams)

    logger.info("diagram_agent_complete", diagram_count=len(diagrams))

    return {
        "diagrams": diagrams,
        "current_step": "diagrams",
        "progress": 0.85,
    }


def _sanitize_mermaid(code: str) -> str:
    """Fix common LLM Mermaid mistakes so the frontend can actually render the diagram.

    Verified against the real mermaid parser (not just assumed) using live LLM output
    that failed exactly these ways:
    - A stray leading "mermaid" line (with or without backticks) left over when the
      LLM nests a ```mermaid fence inside its JSON string value -- the outer JSON
      fence gets stripped by extract_json(), but this inner one doesn't, and mermaid
      then sees "mermaid" where it expects "flowchart"/"classDiagram"/etc.
    - A trailing ">" after a closing pipe in edge labels: -->|label|>
    - An unescaped "(" inside an unquoted [...] node label, e.g. Foo[Page (page.tsx)]
      -- mermaid's flowchart grammar reads "(" as the start of a NEW node shape and
      fails to parse. Deliberately excludes the legitimate cylinder-shape syntax
      ID[(text)], where "(" immediately follows "[".
    """
    code = re.sub(r"^\s*`{0,3}\s*mermaid\s*\r?\n", "", code, flags=re.IGNORECASE)
    code = re.sub(r"\|([^|\n]*)\|>", r"|\1|", code)
    code = re.sub(
        r"(\w+)\[(?!\()([^\[\]\"]*[()][^\[\]\"]*)\]",
        lambda m: f'{m.group(1)}["{m.group(2).replace(chr(34), chr(39))}"]',
        code,
    )
    return code.strip()


def _sanitize_diagrams(diagrams: dict) -> dict:
    result: dict = {}
    for key, value in diagrams.items():
        if key == "sequence_flows" and isinstance(value, dict):
            result[key] = {k: _sanitize_mermaid(v) for k, v in value.items() if isinstance(v, str)}
        elif isinstance(value, str):
            result[key] = _sanitize_mermaid(value)
        else:
            result[key] = value
    return result


def _safe_id(text: str) -> str:
    """Strip characters that break Mermaid node IDs."""
    return "".join(c if c.isalnum() or c == "_" else "_" for c in text)


def _generate_fallback_diagrams(state: AnalysisState) -> dict:
    """Build real diagrams from parsed analysis data without LLM."""
    langs   = state.get("languages") or ["unknown"]
    fws     = state.get("frameworks") or []
    modules = state.get("module_breakdown") or []
    api     = state.get("api_report") or {}
    db      = state.get("database_report") or {}
    entities = db.get("entities") or []
    endpoints = (api.get("endpoints") or [])[:12]

    # ── Architecture: module dependency graph ─────────────────────────────────
    if modules:
        lines = ["flowchart TD"]
        seen_nodes: set[str] = set()
        for mod in modules[:10]:
            name = mod.get("module", "?")
            nid  = _safe_id(name)
            label = name.replace('"', "'")
            if nid not in seen_nodes:
                lines.append(f'    {nid}["{label}"]')
                seen_nodes.add(nid)
            for dep in (mod.get("dependencies") or [])[:4]:
                did = _safe_id(dep)
                dep_label = dep.replace('"', "'")
                if did not in seen_nodes:
                    lines.append(f'    {did}["{dep_label}"]')
                    seen_nodes.add(did)
                lines.append(f'    {nid} --> {did}')
        arch = "\n".join(lines)
    else:
        stack = (langs[0] if not fws else f"{langs[0]}_{fws[0]}").replace(" ", "_")
        arch = f"""flowchart TD
    Client([Client]) --> API[{stack} API]
    API --> Logic[Business Logic]
    Logic --> DB[(Database)]
    Logic --> Cache[(Cache)]"""

    # ── ER diagram from DB entities ───────────────────────────────────────────
    er_diagram = None
    if entities:
        lines = ["erDiagram"]
        for entity in entities[:8]:
            ename = _safe_id(entity.get("name", "Entity"))
            cols  = entity.get("columns") or []
            lines.append(f'    {ename} {{')
            for col in cols[:6]:
                cname = _safe_id(col.get("name", "field"))
                ctype = col.get("type", "string").split("(")[0].strip()
                ctype = _safe_id(ctype) or "string"
                lines.append(f'        {ctype} {cname}')
            lines.append('    }')
        for entity in entities[:8]:
            ename = _safe_id(entity.get("name", "Entity"))
            for rel in (entity.get("relationships") or [])[:3]:
                rname = _safe_id(rel)
                lines.append(f'    {ename} ||--o{{ {rname} : "has"')
        er_diagram = "\n".join(lines)

    # ── Dependency graph: API endpoints ──────────────────────────────────────
    dep_graph = None
    if endpoints:
        lines = ["flowchart LR"]
        lines.append('    Client([Client])')
        for ep in endpoints:
            method = (ep.get("method") or "GET").upper()
            path   = ep.get("path", "/")
            eid    = _safe_id(f"{method}_{path}")
            label  = f"{method} {path}".replace('"', "'")
            lines.append(f'    {eid}["{label}"]')
            lines.append(f'    Client --> {eid}')
        dep_graph = "\n".join(lines)

    return {
        "architecture":    arch,
        "class_diagram":   None,
        "sequence_flows":  {},
        "er_diagram":      er_diagram,
        "dependency_graph": dep_graph,
    }
