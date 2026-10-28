from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class NodeType(StrEnum):
    FILE = "File"
    MODULE = "Module"
    FUNCTION = "Function"
    CLASS = "Class"
    API_ENDPOINT = "APIEndpoint"
    DB_TABLE = "DBTable"
    SERVICE = "Service"


class RelationshipType(StrEnum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"
    QUERIES = "QUERIES"
    DEFINES = "DEFINES"
    BELONGS_TO = "BELONGS_TO"


class GraphNode(BaseModel):
    id: str
    type: NodeType
    name: str
    repo_id: str
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    language: str | None = None
    metadata: dict = {}


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relationship: RelationshipType
    metadata: dict = {}
