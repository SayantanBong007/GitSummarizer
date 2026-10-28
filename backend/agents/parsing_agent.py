from __future__ import annotations

from pathlib import Path

from backend.agents.state import AnalysisState, ParsedFile
from backend.core.logging import get_logger
from backend.embeddings.pipeline import embed_and_store
from backend.knowledge_graph.builder import KnowledgeGraphBuilder
from backend.parsers import get_parser_for

logger = get_logger(__name__)

_MAX_FILE_SIZE = 512 * 1024  # 512 KB — skip minified / generated files
_MAX_FILES = 2000


async def parsing_agent(state: AnalysisState) -> AnalysisState:
    repo_path = Path(state["local_path"])
    repo_id = state["repo_id"]
    file_tree = state["file_tree"]

    parseable = [
        p for p, meta in file_tree.items()
        if meta.get("language") and meta["size"] <= _MAX_FILE_SIZE
    ][:_MAX_FILES]

    logger.info("parsing_agent_start", repo_id=repo_id, files=len(parseable))

    parsed_files: list[ParsedFile] = []
    for rel_path in parseable:
        full_path = repo_path / rel_path
        if not full_path.exists():
            continue
        parser = get_parser_for(full_path)
        if parser is None:
            continue
        result = parser.parse_file(full_path)
        if result:
            result["path"] = rel_path
            parsed_files.append(result)

    kg_builder = KnowledgeGraphBuilder(repo_id=repo_id)
    kg_builder.build_from_parsed_files(parsed_files)

    try:
        await kg_builder.persist_to_neo4j()
    except Exception as exc:
        logger.warning("neo4j_persist_failed", error=str(exc))

    try:
        await embed_and_store(repo_id=repo_id, parsed_files=parsed_files)
    except Exception as exc:
        logger.warning("embedding_failed", error=str(exc))

    tech_stack = _infer_tech_stack(state, parsed_files)

    logger.info("parsing_agent_complete", repo_id=repo_id, parsed=len(parsed_files))

    return {
        "parsed_files": parsed_files,
        "tech_stack": tech_stack,
        "knowledge_graph": kg_builder.to_state_dict(),
        "current_step": "parsing",
        "progress": 0.25,
    }


def _infer_tech_stack(state: AnalysisState, parsed_files: list[ParsedFile]) -> dict:
    all_imports: list[str] = []
    for pf in parsed_files:
        all_imports.extend(pf.get("imports", []))

    imports_text = " ".join(all_imports).lower()

    detected: dict[str, str | list[str]] = {
        "languages": state["languages"],
        "frameworks": state["frameworks"],
    }

    if "fastapi" in imports_text:
        detected["backend"] = "FastAPI"
    elif "django" in imports_text:
        detected["backend"] = "Django"
    elif "flask" in imports_text:
        detected["backend"] = "Flask"
    elif "express" in imports_text:
        detected["backend"] = "Express.js"

    if "react" in imports_text or "react" in " ".join(state["frameworks"]).lower():
        detected["frontend"] = "React"
    elif "vue" in imports_text:
        detected["frontend"] = "Vue.js"
    elif "angular" in imports_text:
        detected["frontend"] = "Angular"

    if "sqlalchemy" in imports_text:
        detected["orm"] = "SQLAlchemy"
    elif "prisma" in imports_text:
        detected["orm"] = "Prisma"
    elif "mongoose" in imports_text:
        detected["orm"] = "Mongoose"

    if "redis" in imports_text:
        detected["cache"] = "Redis"
    if "celery" in imports_text:
        detected["queue"] = "Celery"
    if "kafka" in imports_text:
        detected["queue"] = "Kafka"

    if "postgresql" in imports_text or "asyncpg" in imports_text:
        detected["database"] = "PostgreSQL"
    elif "mongodb" in imports_text or "pymongo" in imports_text:
        detected["database"] = "MongoDB"
    elif "mysql" in imports_text:
        detected["database"] = "MySQL"

    return detected
