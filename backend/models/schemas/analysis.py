from datetime import datetime

from pydantic import BaseModel


class AnalysisStatus(BaseModel):
    id: str
    repository_id: str
    status: str
    progress: float
    current_step: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TechStackReport(BaseModel):
    frontend: str | None = None
    backend: str | None = None
    database: str | None = None
    cache: str | None = None
    queue: str | None = None
    cloud: str | None = None
    ci_cd: str | None = None
    languages: list[str] = []
    frameworks: list[str] = []
    libraries: list[str] = []
    build_tools: list[str] = []
    other: dict[str, str] = {}


class ArchitectureReport(BaseModel):
    style: str  # monolith | modular_monolith | microservices | etc.
    description: str
    layers: list[dict[str, str]] = []
    patterns: list[str] = []
    strengths: list[str] = []
    concerns: list[str] = []


class APIEndpoint(BaseModel):
    method: str
    path: str
    summary: str
    request_schema: dict | None = None
    response_schema: dict | None = None
    auth_required: bool = False
    tags: list[str] = []


class APIReport(BaseModel):
    type: str  # REST | GraphQL | gRPC | WebSocket | mixed
    base_path: str | None = None
    endpoints: list[APIEndpoint] = []
    authentication: str | None = None
    versioning: str | None = None


class DBEntity(BaseModel):
    name: str
    description: str
    columns: list[dict[str, str]] = []
    relationships: list[str] = []


class DatabaseReport(BaseModel):
    orm: str | None = None
    database_type: str | None = None
    entities: list[DBEntity] = []
    migrations_present: bool = False
    erd_mermaid: str | None = None


class SecurityFinding(BaseModel):
    severity: str  # critical | high | medium | low | info
    category: str
    description: str
    file_path: str | None = None
    line_number: int | None = None
    recommendation: str


class SecurityReport(BaseModel):
    overall_risk: str  # critical | high | medium | low
    findings: list[SecurityFinding] = []
    authentication_analysis: str | None = None
    authorization_analysis: str | None = None
    summary: str


class DiagramSet(BaseModel):
    architecture: str | None = None   # Mermaid flowchart
    sequence_flows: dict[str, str] = {}  # flow_name -> mermaid sequence
    class_diagram: str | None = None
    er_diagram: str | None = None
    dependency_graph: str | None = None


class AnalysisResult(BaseModel):
    id: str
    repository_id: str
    status: str
    progress: float
    executive_summary: str | None = None
    tech_stack: TechStackReport | None = None
    architecture: ArchitectureReport | None = None
    api_report: APIReport | None = None
    database_report: DatabaseReport | None = None
    security_report: SecurityReport | None = None
    diagrams: DiagramSet | None = None
    design_patterns: list[str] = []
    module_breakdown: list[dict] = []
    markdown_docs: dict[str, str] = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ChatRequest(BaseModel):
    repository_id: str
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    message: ChatMessage
    sources: list[dict] = []
