import { useQuery } from "@tanstack/react-query";
import { getAnalysisStatus, getAnalysisResult } from "@/api/client";
import type { AnalysisStatus, AnalysisResult } from "@/types";

export function useAnalysisStatus(analysisId: string | null) {
  return useQuery<AnalysisStatus>({
    queryKey: ["analysis", "status", analysisId],
    queryFn: () => getAnalysisStatus(analysisId!),
    enabled: !!analysisId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      return data.status === "completed" || data.status === "failed" ? false : 3000;
    },
  });
}

export function useAnalysisResult(analysisId: string | null, enabled = false) {
  return useQuery<AnalysisResult>({
    queryKey: ["analysis", "result", analysisId],
    queryFn: () => getAnalysisResult(analysisId!),
    enabled: !!analysisId && enabled,
  });
}
