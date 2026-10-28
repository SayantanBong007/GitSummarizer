import { Building2, Layers, Puzzle, AlertTriangle, CheckCircle } from "lucide-react";
import type { AnalysisResult } from "@/types";

interface Props {
  result: AnalysisResult;
}

const RISK_COLOR: Record<string, string> = {
  critical: "text-red-600 bg-red-50 border-red-200",
  high: "text-orange-600 bg-orange-50 border-orange-200",
  medium: "text-yellow-600 bg-yellow-50 border-yellow-200",
  low: "text-green-600 bg-green-50 border-green-200",
};

export default function ArchitectureExplorer({ result }: Props) {
  const arch = result.architecture;
  const sec = result.security_report;

  return (
    <div className="space-y-6">
      {arch && (
        <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-3">
            <Building2 className="text-indigo-600" size={20} />
            <div>
              <h3 className="font-semibold text-slate-800">
                Architecture Style: <span className="text-indigo-600">{arch.style}</span>
              </h3>
              <p className="text-sm text-slate-500 mt-1">{arch.description}</p>
            </div>
          </div>

          {arch.layers.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Layers</p>
              <div className="grid grid-cols-1 gap-2">
                {arch.layers.map((layer, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                    <Layers size={16} className="text-slate-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-slate-700">{layer.name}</p>
                      <p className="text-xs text-slate-500">{layer.description}</p>
                      {layer.path && (
                        <code className="text-xs text-indigo-600 mt-1 block">{layer.path}</code>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {arch.patterns.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Design Patterns</p>
              <div className="flex flex-wrap gap-2">
                {arch.patterns.map((p, i) => (
                  <span key={i} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium flex items-center gap-1">
                    <Puzzle size={12} /> {p}
                  </span>
                ))}
              </div>
            </div>
          )}

          {arch.strengths.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Strengths</p>
              <ul className="space-y-1">
                {arch.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <CheckCircle size={14} className="text-green-500 mt-0.5 shrink-0" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {arch.concerns.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Concerns</p>
              <ul className="space-y-1">
                {arch.concerns.map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <AlertTriangle size={14} className="text-yellow-500 mt-0.5 shrink-0" />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {sec && (
        <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-slate-800">Security Overview</h3>
            <span className={`text-xs font-semibold px-2 py-1 rounded border ${RISK_COLOR[sec.overall_risk] ?? "text-slate-600 bg-slate-50 border-slate-200"}`}>
              {sec.overall_risk.toUpperCase()}
            </span>
          </div>
          <p className="text-sm text-slate-600">{sec.summary}</p>
          {sec.findings.slice(0, 5).map((f, i) => (
            <div key={i} className={`p-3 rounded-lg border text-sm ${RISK_COLOR[f.severity] ?? "bg-slate-50 border-slate-200 text-slate-600"}`}>
              <p className="font-medium">{f.category}</p>
              <p className="opacity-80">{f.description}</p>
              {f.file_path && <code className="text-xs">{f.file_path}{f.line_number ? `:${f.line_number}` : ""}</code>}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
