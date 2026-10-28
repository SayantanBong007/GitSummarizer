import axios from "axios";
import type {
  AnalysisResult,
  AnalysisStatus,
  ChatMessage,
  ChatResponse,
  GraphEdge,
  GraphNode,
  Repository,
  RepositoryListResponse,
  SubmitResponse,
} from "@/types";

export type { RepositoryListResponse };

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 90_000,  // 90s — chat needs time for 3-model fallback chain
});

export const submitRepository = (url: string): Promise<SubmitResponse> =>
  api.post("/repositories/", { url }).then((r) => r.data);

export const listRepositories = (offset = 0, limit = 20): Promise<RepositoryListResponse> =>
  api.get("/repositories/", { params: { offset, limit } }).then((r) => r.data);

export const getRepository = (repoId: string): Promise<Repository> =>
  api.get(`/repositories/${repoId}`).then((r) => r.data);

export const getAnalysisStatus = (analysisId: string): Promise<AnalysisStatus> =>
  api.get(`/analysis/${analysisId}/status`).then((r) => r.data);

export const getAnalysisResult = (analysisId: string): Promise<AnalysisResult> =>
  api.get(`/analysis/${analysisId}/result`).then((r) => r.data);

export const getRepoAnalysisStatus = (repoId: string): Promise<AnalysisStatus | null> =>
  api.get(`/repositories/${repoId}/analysis`).then((r) => r.data);

export const exportJson = (analysisId: string): string =>
  `/api/v1/analysis/${analysisId}/export/json`;

export const exportPdf = (analysisId: string): string =>
  `/api/v1/analysis/${analysisId}/export/pdf`;

export const getRepoGraph = (repoId: string): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> =>
  api.get(`/repositories/${repoId}/graph`).then((r) => r.data);

export const reanalyzeRepository = (repoId: string): Promise<{ analysis_id: string }> =>
  api.post(`/repositories/${repoId}/reanalyze`).then((r) => r.data);

export const chatWithRepo = (
  repositoryId: string,
  messages: ChatMessage[]
): Promise<ChatResponse> =>
  api.post("/chat/", { repository_id: repositoryId, messages }).then((r) => r.data);
