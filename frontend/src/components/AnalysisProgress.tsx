import { motion, AnimatePresence } from "framer-motion";
import {
  GitBranch, Code2, GitGraph, FileText,
  CheckCircle2, XCircle, Loader2, Clock, Zap,
} from "lucide-react";
import type { StepEvent } from "@/types";
import type { StreamStatus } from "@/hooks/useAnalysisStream";

const STEP_META: Record<string, { label: string; Icon: React.ElementType }> = {
  repo:          { label: "Clone Repository",            Icon: GitBranch },
  parse:         { label: "Parse Code (AST + Symbols)",  Icon: Code2     },
  analyze:       { label: "Deep Analysis (5 agents)",     Icon: Zap       },
  diagram:       { label: "Generate Diagrams",            Icon: GitGraph  },
  documentation: { label: "Write Documentation",          Icon: FileText  },
};

const STEP_ORDER = ["repo", "parse", "analyze", "diagram", "documentation"];

interface Props {
  events:       StepEvent[];
  streamStatus: StreamStatus;
  progress:     number;
  currentStep:  string | null;
  errorMessage: string | null;
}

export default function AnalysisProgress({
  events, streamStatus, progress, currentStep, errorMessage,
}: Props) {
  const pct           = Math.round(progress * 100);
  const completedSteps = new Set(events.map((e) => e.step));
  const eventByStep   = Object.fromEntries(events.map((e) => [e.step, e]));

  return (
    <div className="w-full max-w-2xl mx-auto bg-white border border-slate-200 rounded-2xl shadow-card p-6">
      {/* Progress bar */}
      <div className="mb-7">
        <div className="flex justify-between text-xs mb-2">
          <span className="tracking-wider uppercase font-semibold text-slate-400">
            {streamStatus === "connecting" ? "Connecting…"  :
             streamStatus === "completed"  ? "Complete"     :
             streamStatus === "failed"     ? "Failed"       : "Analysing"}
          </span>
          <span className="tabular-nums font-semibold text-indigo-600">{pct}%</span>
        </div>
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${
              streamStatus === "failed"    ? "bg-red-500"    :
              streamStatus === "completed" ? "bg-emerald-500": "bg-indigo-500"
            }`}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
      </div>

      {/* Step list */}
      <div className="space-y-1.5">
        {STEP_ORDER.map((stepId) => {
          const meta    = STEP_META[stepId];
          if (!meta) return null;
          const { label, Icon } = meta;
          const isDone   = completedSteps.has(stepId);
          const isActive = currentStep === stepId && !isDone && streamStatus === "running";
          const event    = eventByStep[stepId] as StepEvent | undefined;

          if (isDone && event) {
            return (
              <motion.div
                key={stepId}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className="py-2.5 px-3 rounded-xl bg-emerald-50/60"
              >
                <div className="flex items-center gap-3">
                  <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
                  <Icon size={14} className="text-slate-400 shrink-0" />
                  <span className="text-slate-700 font-medium flex-1 text-sm">{label}</span>
                  <span className="text-slate-400 tabular-nums text-xs font-mono flex items-center gap-1">
                    <Clock size={10} /> {event.duration}s
                  </span>
                </div>
                {event.headline && (
                  <p className="ml-[52px] mt-1 text-xs text-slate-500 leading-relaxed font-mono">
                    {event.headline}
                  </p>
                )}
              </motion.div>
            );
          }

          if (isActive) {
            return (
              <motion.div
                key={stepId}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="py-2.5 px-3 rounded-xl bg-indigo-50 border border-indigo-100"
              >
                <div className="flex items-center gap-3">
                  <Loader2 size={15} className="text-indigo-500 animate-spin shrink-0" />
                  <Icon size={14} className="text-indigo-500 shrink-0" />
                  <span className="text-indigo-700 font-medium flex-1 text-sm">{label}</span>
                  <span className="text-indigo-400 text-xs animate-pulse font-mono">running…</span>
                </div>
              </motion.div>
            );
          }

          return (
            <div key={stepId} className="py-2.5 px-3 flex items-center gap-3 opacity-40">
              <div className="w-[15px] h-[15px] rounded-full border-2 border-slate-200 shrink-0" />
              <Icon size={14} className="text-slate-300 shrink-0" />
              <span className="text-slate-400 text-sm">{label}</span>
            </div>
          );
        })}
      </div>

      {/* Error */}
      <AnimatePresence>
        {streamStatus === "failed" && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-6 flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-600"
          >
            <XCircle size={14} className="shrink-0 mt-0.5" />
            <span>{errorMessage ?? "Analysis failed."}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Parallel-agents legend */}
      {(currentStep === "analyze" || completedSteps.has("analyze")) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-4 p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-500"
        >
          <span className="text-indigo-600 font-semibold">⚡ Sequential agents: </span>
          Architecture · API / Backend · Frontend · Database · Security
        </motion.div>
      )}
    </div>
  );
}
