import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState } from "react";
import { FileText, Download } from "lucide-react";
import { exportJson, exportPdf } from "@/api/client";

interface Props {
  docs: Record<string, string>;
  executiveSummary: string | null;
  analysisId: string;
}

const DOC_ORDER = [
  "executive_summary.md",
  "architecture.md",
  "api.md",
  "database.md",
  "security.md",
  "onboarding.md",
];

export default function DocumentationViewer({ docs, executiveSummary, analysisId }: Props) {
  const allDocs: Record<string, string> = {};
  if (executiveSummary) {
    allDocs["executive_summary.md"] = executiveSummary;
  }
  Object.assign(allDocs, docs);

  const keys = [
    ...DOC_ORDER.filter((k) => k in allDocs),
    ...Object.keys(allDocs).filter((k) => !DOC_ORDER.includes(k)),
  ];

  const [active, setActive] = useState<string>(keys[0] ?? "");

  return (
    <div className="flex gap-4 h-full">
      <aside className="w-44 shrink-0 space-y-1">
        {keys.map((key) => (
          <button
            key={key}
            onClick={() => setActive(key)}
            className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
              active === key
                ? "bg-indigo-50 text-indigo-700 font-medium"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            <FileText size={14} />
            <span className="truncate">{key.replace(".md", "").replace(/_/g, " ")}</span>
          </button>
        ))}

        <div className="pt-4 border-t border-slate-100 space-y-1">
          <a
            href={exportJson(analysisId)}
            download
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-600 hover:bg-slate-50"
          >
            <Download size={14} /> JSON
          </a>
          <a
            href={exportPdf(analysisId)}
            download
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-600 hover:bg-slate-50"
          >
            <Download size={14} /> PDF
          </a>
        </div>
      </aside>

      <div className="flex-1 overflow-auto bg-white border border-slate-200 rounded-xl p-6">
        {allDocs[active] ? (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            className="prose prose-sm max-w-none prose-headings:text-slate-800 prose-code:text-indigo-700"
          >
            {allDocs[active]}
          </ReactMarkdown>
        ) : (
          <p className="text-slate-400 text-sm">Select a document from the sidebar.</p>
        )}
      </div>
    </div>
  );
}
