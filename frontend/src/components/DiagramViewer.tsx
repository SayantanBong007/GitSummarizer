import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { Copy, Check, AlertCircle } from "lucide-react";
import type { DiagramSet } from "@/types";

mermaid.initialize({
  startOnLoad: false,
  theme:         "dark",
  securityLevel: "loose",
  fontFamily:    "ui-monospace, monospace",
});

function sanitizeMermaid(code: string): string {
  return code
    // The backend (diagram_agent.py) sanitizes this same way at the source, so
    // this is mostly a defensive net for anything stored before that fix, or any
    // gap between the two implementations.
    //
    // A stray leading "mermaid" line (with or without backticks) left over when
    // the LLM nests a ```mermaid fence inside its JSON string value -- verified
    // live: every diagram for one real repo started with a literal "mermaid"
    // line before "flowchart TD"/"classDiagram"/etc., which mermaid can't parse.
    .replace(/^\s*`{0,3}\s*mermaid\s*\r?\n/i, "")
    // LLMs often emit -->|label|> — strip the trailing >
    .replace(/\|([^|\n]*)\|>/g, "|$1|")
    // Also fix -.|label|> (dotted arrows)
    .replace(/\-\.\|([^|\n]*)\|>/g, "-.|$1|")
    // A bare "(" inside an unquoted [...] node label makes mermaid's flowchart
    // grammar think a new node shape is starting (e.g. Dashboard[Page (page.tsx)]
    // fails to parse: "Expecting ... got 'PS'"). Wrap any such label in quotes,
    // but NOT the legitimate cylinder-shape syntax ID[(text)], where "(" is the
    // very first character after "[".
    // Verified against the real mermaid parser against live LLM-generated
    // diagrams that failed exactly this way before this fix.
    .replace(/(\w+)\[(?!\()([^\[\]"]*[()][^\[\]"]*)\]/g, (_m, id, label) => `${id}["${label.replace(/"/g, "'")}"]`)
    .trim();
}

type DiagramKey = keyof Pick<DiagramSet, "architecture" | "class_diagram" | "er_diagram" | "dependency_graph">;

const TABS: { key: DiagramKey | "sequence"; label: string }[] = [
  { key: "architecture",    label: "Architecture"  },
  { key: "class_diagram",   label: "Class Diagram" },
  { key: "er_diagram",      label: "ER Diagram"    },
  { key: "dependency_graph", label: "Dependencies" },
  { key: "sequence",        label: "Flows"         },
];

interface Props {
  diagrams: DiagramSet;
}

export default function DiagramViewer({ diagrams }: Props) {
  const [activeTab,  setActiveTab]  = useState<string>("architecture");
  const [activeFlow, setActiveFlow] = useState<string>("");
  const [renderErr,  setRenderErr]  = useState<string | null>(null);
  const [copied,     setCopied]     = useState(false);
  const [rendering,  setRendering]  = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const renderIdRef  = useRef(0);

  const flowNames = Object.keys(diagrams.sequence_flows ?? {});

  const getMermaidCode = (): string | null => {
    const raw = activeTab === "sequence"
      ? diagrams.sequence_flows?.[activeFlow] ?? null
      : diagrams[activeTab as DiagramKey] ?? null;
    return raw ? sanitizeMermaid(raw) : null;
  };

  const code = getMermaidCode();

  // Keep first flow selected
  useEffect(() => {
    if (flowNames.length > 0 && !activeFlow) setActiveFlow(flowNames[0]);
  }, [flowNames.join(",")]);

  // Re-render whenever the active code changes
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!code) {
      el.innerHTML = "";
      setRenderErr(null);
      return;
    }

    const renderId = ++renderIdRef.current;
    setRenderErr(null);
    setRendering(true);
    el.innerHTML = "";

    const uniqueId = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2)}`;

    mermaid
      .render(uniqueId, code)
      .then(({ svg }) => {
        if (renderId !== renderIdRef.current) return; // stale render
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
          // make SVG responsive
          const svgEl = containerRef.current.querySelector("svg");
          if (svgEl) {
            svgEl.removeAttribute("height");
            svgEl.style.width  = "100%";
            svgEl.style.height = "auto";
            svgEl.style.maxHeight = "600px";
          }
        }
        setRendering(false);
      })
      .catch((err: unknown) => {
        if (renderId !== renderIdRef.current) return;
        const msg = err instanceof Error ? err.message : String(err);
        setRenderErr(msg);
        setRendering(false);
      });
  }, [code]);

  const handleCopy = () => {
    if (!code) return;
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const availableTabs = TABS.filter((t) =>
    t.key === "sequence" ? flowNames.length > 0 : !!diagrams[t.key as DiagramKey]
  );

  if (availableTabs.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
        No diagrams were generated for this repository.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <div className="flex flex-wrap gap-2">
        {availableTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Flow sub-tabs */}
      {activeTab === "sequence" && flowNames.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {flowNames.map((name) => (
            <button
              key={name}
              onClick={() => setActiveFlow(name)}
              className={`px-3 py-1 rounded text-xs font-medium ${
                activeFlow === name
                  ? "bg-indigo-100 text-indigo-700"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {name}
            </button>
          ))}
        </div>
      )}

      {/* Diagram area */}
      <div className="relative rounded-xl border border-slate-200 bg-slate-950 overflow-hidden">
        {/* Toolbar */}
        <div className="absolute top-3 right-3 z-10 flex gap-2">
          {code && (
            <button
              onClick={handleCopy}
              title="Copy Mermaid source"
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 text-xs transition-colors"
            >
              {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
              {copied ? "Copied" : "Copy code"}
            </button>
          )}
        </div>

        {rendering && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/80 z-10">
            <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {renderErr ? (
          <div className="p-4 space-y-3">
            <div className="flex items-center gap-2 text-amber-400 text-sm">
              <AlertCircle size={16} />
              <span>Diagram could not be rendered — showing source</span>
            </div>
            <pre className="text-xs text-slate-400 overflow-auto max-h-64 p-3 bg-slate-900 rounded-lg">
              {code}
            </pre>
          </div>
        ) : (
          <div
            ref={containerRef}
            className="p-6 min-h-64 overflow-auto flex justify-center"
          />
        )}
      </div>
    </div>
  );
}
