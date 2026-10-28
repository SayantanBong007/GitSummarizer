import { useEffect } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { GitBranch } from "lucide-react";
import AnalysisProgress from "@/components/AnalysisProgress";
import { useAnalysisStream } from "@/hooks/useAnalysisStream";

export default function AnalysisPage() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const [searchParams] = useSearchParams();
  const repoId = searchParams.get("repo");
  const navigate = useNavigate();

  const { events, streamStatus, progress, currentStep, errorMessage } =
    useAnalysisStream(analysisId ?? null);

  useEffect(() => {
    if (streamStatus === "completed" && repoId) {
      setTimeout(() => navigate(`/results/${repoId}`), 1200);
    }
  }, [streamStatus, repoId, navigate]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="mb-8 flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center shadow-glow shrink-0">
            <GitBranch size={15} className="text-white" />
          </div>
          <span className="font-semibold text-slate-800 tracking-tight">GitSummarize</span>
          {analysisId && (
            <span className="ml-auto text-slate-400 text-xs font-mono bg-slate-100 px-2 py-1 rounded-full">
              {analysisId.slice(0, 8)}…
            </span>
          )}
        </div>

        <AnalysisProgress
          events={events}
          streamStatus={streamStatus}
          progress={progress}
          currentStep={currentStep}
          errorMessage={errorMessage}
        />

        {streamStatus === "completed" && (
          <p className="mt-6 text-center text-sm text-slate-400 animate-pulse">
            Loading results…
          </p>
        )}
      </div>
    </div>
  );
}
