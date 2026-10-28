export interface RepositoryListResponse {
  items: Repository[];
  total: number;
}

export interface Repository {
  id: string;
  url: string;
  owner: string;
  name: string;
  default_branch: string | null;
  description: string | null;
  stars: number | null;
  languages: string[] | null;
  frameworks: string[] | null;
  clone_status: "pending" | "cloning" | "cloned" | "error";
  created_at: string;
  updated_at: string;
}

export interface AnalysisStatus {
  id: string;
  repository_id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  current_step: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface StepEvent {
  type: "step";
  step: string;
  progress: number;
  current_step: string;
  headline: string;
  duration: number;
  timestamp: string;
}

export interface APIEndpoint {
  method: string;
  path: string;
  summary: string;
  auth_required: boolean;
  tags: string[];
}

export interface APIReport {
  type: string;
  base_path: string | null;
  authentication: string | null;
  versioning: string | null;
  endpoints: APIEndpoint[];
  services: Array<{ name: string; responsibility: string; methods: string[] }>;
}

export interface DBEntity {
  name: string;
  description: string;
  columns: Array<{ name: string; type: string; nullable: string }>;
  relationships: string[];
}

export interface DatabaseReport {
  orm: string | null;
  database_type: string | null;
  migrations_present: boolean;
  entities: DBEntity[];
  erd_mermaid: string | null;
}

export interface SecurityFinding {
  severity: "critical" | "high" | "medium" | "low" | "info";
  category: string;
  description: string;
  file_path: string | null;
  line_number: number | null;
  recommendation: string;
}

export interface SecurityReport {
  overall_risk: string;
  summary: string;
  findings: SecurityFinding[];
  authentication_analysis: string | null;
  authorization_analysis: string | null;
}

export interface DiagramSet {
  architecture: string | null;
  class_diagram: string | null;
  sequence_flows: Record<string, string>;
  er_diagram: string | null;
  dependency_graph: string | null;
}

export interface AnalysisResult {
  id: string;
  repository_id: string;
  status: string;
  progress: number;
  executive_summary: string | null;
  tech_stack: Record<string, string | string[]> | null;
  architecture: {
    style: string;
    description: string;
    layers: Array<{ name: string; description: string; path: string }>;
    patterns: string[];
    strengths: string[];
    concerns: string[];
  } | null;
  api_report: APIReport | null;
  database_report: DatabaseReport | null;
  security_report: SecurityReport | null;
  diagrams: DiagramSet | null;
  design_patterns: string[];
  module_breakdown: Array<{
    module: string;
    responsibility: string;
    public_interfaces: string[];
    dependencies: string[];
    internal_flow: string;
  }>;
  markdown_docs: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatSource {
  file: string;
  symbol: string;
  score: number;
}

export interface ChatResponse {
  message: ChatMessage;
  sources: ChatSource[];
}

export interface SubmitResponse {
  repository_id: string;
  analysis_id: string;
  message: string;
}

export interface GraphNode {
  id: string;
  type: string;
  name: string;
  file_path?: string | null;
}

export interface GraphEdge {
  source_id: string;
  target_id: string;
  relationship: string;
}
