from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.state import AnalysisState
from backend.core.logging import get_logger
from backend.llm.context import build_context
from backend.llm.client import get_fast_llm
from backend.llm.utils import extract_json

logger = get_logger(__name__)

_DB_KEYWORDS   = {"model", "schema", "migration", "entity", "table", "orm", "db", "database", "repository", "prisma", "sequelize", "mongoose"}
_DB_EXTENSIONS = {".py", ".ts", ".js", ".java", ".go", ".prisma", ".sql"}

SYSTEM_PROMPT = (
    "You are a database architect. "
    "Respond ONLY with a single valid JSON object — no markdown fences, no explanation."
)

ANALYSIS_PROMPT = """Analyze the database layer of this repository and return a JSON object with EXACTLY this schema:

{{
  "orm": "<SQLAlchemy|Prisma|Mongoose|Hibernate|GORM|TypeORM|Sequelize|None|unknown>",
  "database_type": "<PostgreSQL|MySQL|SQLite|MongoDB|DynamoDB|Redis|unknown>",
  "migrations_present": <true|false>,
  "entities": [
    {{
      "name": "<table or model name>",
      "description": "<what data this entity stores>",
      "columns": [
        {{"name": "<column>", "type": "<str|int|bool|datetime|uuid|json|etc>", "nullable": "<yes|no>"}}
      ],
      "relationships": ["<related entity names>"]
    }}
  ],
  "erd_mermaid": "<complete erDiagram mermaid code showing all entities and their relationships, or null>"
}}

=== Database / model / schema files ===
{code_snippets}
"""


async def database_agent(state: AnalysisState) -> dict:
    llm     = get_fast_llm(temperature=0.1, max_tokens=1500)
    context = build_context(
        state.get("parsed_files", []),
        keywords=_DB_KEYWORDS,
        extensions=_DB_EXTENSIONS,
        max_files=10,
    )

    if not context:
        return {"database_report": None, "current_step": "database", "progress": 0.65}

    prompt = ANALYSIS_PROMPT.format(code_snippets=context)

    try:
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        data = extract_json(str(response.content))
    except Exception as exc:
        logger.warning("database_agent_error", error=str(exc))
        data = {"orm": "unknown", "database_type": "unknown", "entities": []}

    logger.info("database_agent_complete", entities=len(data.get("entities", [])))
    return {"database_report": data, "current_step": "database", "progress": 0.65}
