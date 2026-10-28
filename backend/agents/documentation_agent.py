from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.state import AnalysisState
from backend.core.logging import get_logger
from backend.llm.router import TaskType, get_router

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior technical writer producing professional software documentation.
Write in clear, structured Markdown. Be thorough and precise."""

EXECUTIVE_PROMPT = """Write an executive summary for this repository as Markdown.

Cover:
1. What the project does and the problem it solves
2. Target users / stakeholders
3. High-level architecture overview
4. Main technologies
5. Key strengths and notable concerns

Repository:
- Name: {repo_name}
- Languages: {languages}
- Frameworks: {frameworks}
- Architecture: {arch_style} — {arch_desc}
- API type: {api_type}
- Security risk: {security_risk}

Write 4-6 paragraphs. Professional tone."""

ONBOARDING_PROMPT = (
    "Write an onboarding guide for a new engineer joining this project as Markdown.\n"
    "\nCover:\n"
    "1. Project overview (what it does)\n"
    "2. Prerequisites and environment setup\n"
    "3. Repository structure walkthrough\n"
    "4. Key concepts to understand first\n"
    "5. How to run the project locally\n"
    "6. Where to make common types of changes\n"
    "\nUse: {repo_name}, {languages}, {frameworks}, {arch_style}\n"
    "File structure: {file_tree_sample}"
)


async def documentation_agent(state: AnalysisState) -> AnalysisState:
    llm = get_router().get(TaskType.GENERATE)

    arch = state.get("architecture_report") or {}
    api = state.get("api_report") or {}
    sec = state.get("security_report") or {}

    executive_summary = await _generate_executive_summary(llm, state, arch, api, sec)
    markdown_docs = await _generate_markdown_docs(llm, state, arch, api)

    logger.info("documentation_agent_complete", docs=list(markdown_docs.keys()))

    return {
        "executive_summary": executive_summary,
        "markdown_docs": markdown_docs,
        "current_step": "documentation",
        "progress": 1.0,
    }


async def _generate_executive_summary(llm, state, arch, api, sec) -> str:
    prompt = EXECUTIVE_PROMPT.format(
        repo_name=state.get("repo_name", "unknown"),
        languages=", ".join(state.get("languages", [])),
        frameworks=", ".join(state.get("frameworks", [])),
        arch_style=arch.get("style", "unknown"),
        arch_desc=arch.get("description", ""),
        api_type=api.get("type", "unknown"),
        security_risk=sec.get("overall_risk", "unknown"),
    )
    try:
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        return str(response.content).strip()
    except Exception as exc:
        logger.warning("executive_summary_error", error=str(exc))
        return f"# {state.get('repo_name', 'Repository')} Overview\n\nAnalysis completed."


async def _generate_markdown_docs(llm, state, arch, api) -> dict[str, str]:
    docs: dict[str, str] = {}

    docs["architecture.md"] = _render_architecture_doc(state, arch)
    docs["api.md"] = _render_api_doc(state, api)
    docs["database.md"] = _render_database_doc(state)
    docs["security.md"] = _render_security_doc(state)
    docs["onboarding.md"] = await _generate_onboarding(llm, state, arch)

    return docs


def _render_architecture_doc(state: AnalysisState, arch: dict) -> str:
    lines = [f"# Architecture — {state.get('repo_name', 'Repository')}\n"]
    lines.append(f"**Style:** {arch.get('style', 'unknown')}\n")
    lines.append(f"{arch.get('description', '')}\n")

    if arch.get("layers"):
        lines.append("## Layers\n")
        for layer in arch["layers"]:
            lines.append(f"### {layer.get('name', '')}")
            lines.append(f"{layer.get('description', '')}")
            if layer.get("path"):
                lines.append(f"*Path pattern:* `{layer['path']}`\n")

    if arch.get("patterns"):
        lines.append("## Design Patterns\n")
        for p in arch["patterns"]:
            lines.append(f"- {p}")
        lines.append("")

    diagrams = state.get("diagrams", {})
    if diagrams.get("architecture"):
        lines.append("## Architecture Diagram\n")
        lines.append("```mermaid")
        lines.append(diagrams["architecture"])
        lines.append("```\n")

    if diagrams.get("class_diagram"):
        lines.append("## Class Diagram\n")
        lines.append("```mermaid")
        lines.append(diagrams["class_diagram"])
        lines.append("```\n")

    if arch.get("concerns"):
        lines.append("## Concerns\n")
        for c in arch["concerns"]:
            lines.append(f"- {c}")

    return "\n".join(lines)


def _render_api_doc(state: AnalysisState, api: dict) -> str:
    lines = [f"# API Reference — {state.get('repo_name', 'Repository')}\n"]
    lines.append(f"**Type:** {api.get('type', 'unknown')}  ")
    lines.append(f"**Authentication:** {api.get('authentication', 'unknown')}  ")
    lines.append(f"**Base Path:** `{api.get('base_path', '/')}`\n")

    endpoints = api.get("endpoints", [])
    if endpoints:
        lines.append("## Endpoints\n")
        lines.append("| Method | Path | Summary | Auth |")
        lines.append("|--------|------|---------|------|")
        for ep in endpoints:
            auth = "✓" if ep.get("auth_required") else "—"
            lines.append(
                f"| `{ep.get('method', 'GET')}` | `{ep.get('path', '/')}` "
                f"| {ep.get('summary', '')} | {auth} |"
            )

    diagrams = state.get("diagrams", {})
    for name, mermaid in diagrams.get("sequence_flows", {}).items():
        lines.append(f"\n## {name} Flow\n")
        lines.append("```mermaid")
        lines.append(mermaid)
        lines.append("```")

    return "\n".join(lines)


def _render_database_doc(state: AnalysisState) -> str:
    db = state.get("database_report") or {}
    lines = [f"# Database — {state.get('repo_name', 'Repository')}\n"]
    lines.append(f"**ORM:** {db.get('orm', 'unknown')}  ")
    lines.append(f"**Database:** {db.get('database_type', 'unknown')}  ")
    lines.append(f"**Migrations:** {'Yes' if db.get('migrations_present') else 'No'}\n")

    for entity in db.get("entities", []):
        lines.append(f"## {entity.get('name', 'Entity')}")
        lines.append(f"{entity.get('description', '')}\n")
        if entity.get("columns"):
            lines.append("| Column | Type | Nullable |")
            lines.append("|--------|------|----------|")
            for col in entity["columns"]:
                nullable = col.get('nullable', 'yes')
                lines.append(
                    f"| {col.get('name')} | {col.get('type')} | {nullable} |"
                )
        if entity.get("relationships"):
            lines.append(f"\n**Relationships:** {', '.join(entity['relationships'])}\n")

    if db.get("erd_mermaid"):
        lines.append("## ERD\n")
        lines.append("```mermaid")
        lines.append(db["erd_mermaid"])
        lines.append("```")

    return "\n".join(lines)


def _render_security_doc(state: AnalysisState) -> str:
    sec = state.get("security_report") or {}
    lines = [f"# Security Report — {state.get('repo_name', 'Repository')}\n"]
    risk = sec.get("overall_risk", "unknown").upper()
    lines.append(f"**Overall Risk:** {risk}\n")
    lines.append(f"{sec.get('summary', '')}\n")

    if sec.get("authentication_analysis"):
        lines.append("## Authentication")
        lines.append(sec["authentication_analysis"])
    if sec.get("authorization_analysis"):
        lines.append("\n## Authorization")
        lines.append(sec["authorization_analysis"])

    findings = sec.get("findings", [])
    if findings:
        lines.append("\n## Findings\n")
        for f in findings:
            sev = f.get("severity", "info").upper()
            lines.append(f"### [{sev}] {f.get('category', 'Finding')}")
            lines.append(f"{f.get('description', '')}")
            if f.get("file_path"):
                loc = f["file_path"]
                if f.get("line_number"):
                    loc += f":{f['line_number']}"
                lines.append(f"*Location:* `{loc}`")
            lines.append(f"**Recommendation:** {f.get('recommendation', '')}\n")

    return "\n".join(lines)


async def _generate_onboarding(llm, state, arch) -> str:
    file_tree_sample = "\n".join(list(state.get("file_tree", {}).keys())[:30])
    prompt = ONBOARDING_PROMPT.format(
        repo_name=state.get("repo_name", "Repository"),
        languages=", ".join(state.get("languages", [])),
        frameworks=", ".join(state.get("frameworks", [])),
        arch_style=arch.get("style", "unknown"),
        file_tree_sample=file_tree_sample,
    )
    try:
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        return str(response.content).strip()
    except Exception as exc:
        logger.warning("onboarding_doc_error", error=str(exc))
        repo_name = state.get('repo_name', 'this project')
        return (
            f"# Getting Started with {repo_name}\n\n"
            "See README for setup instructions."
        )
