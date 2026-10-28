import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Building2, FileText, GitGraph, MessageSquare, Network, ArrowLeft,
  Loader2, Shield, Database, Zap, Code2, CheckCircle, AlertTriangle,
  XCircle, ChevronRight, Download, Lock, RefreshCw,
} from "lucide-react";
import { getRepoAnalysisStatus, getAnalysisResult, exportJson, reanalyzeRepository } from "@/api/client";
import { toast } from "sonner";
import DiagramViewer from "@/components/DiagramViewer";
import DocumentationViewer from "@/components/DocumentationViewer";
import ChatInterface from "@/components/ChatInterface";
import GraphViewer from "@/components/GraphViewer";
import type { AnalysisResult } from "@/types";

// ── Types ────────────────────────────────────────────────────────────────────

type Tab = "overview" | "api" | "database" | "security" | "diagrams" | "docs" | "chat" | "graph";

// ── Knowledge-graph builder from AnalysisResult ───────────────────────────────

interface KGNode { id: string; type: string; name: string; file_path?: string }
interface KGEdge { source_id: string; target_id: string; relationship: string }

function buildKnowledgeGraph(result: AnalysisResult): { nodes: KGNode[]; edges: KGEdge[] } {
  const nodes: KGNode[] = [];
  const edges: KGEdge[] = [];
  const seen = new Set<string>();

  const add = (n: KGNode) => { if (!seen.has(n.id)) { seen.add(n.id); nodes.push(n); } };

  // Modules from architecture module_breakdown
  for (const mod of result.module_breakdown ?? []) {
    add({ id: `mod:${mod.module}`, type: "Module", name: mod.module });
    for (const dep of mod.dependencies ?? []) {
      add({ id: `mod:${dep}`, type: "Module", name: dep });
      edges.push({ source_id: `mod:${mod.module}`, target_id: `mod:${dep}`, relationship: "IMPORTS" });
    }
  }

  // API endpoints (capped at 20 for readability)
  const endpoints = result.api_report?.endpoints ?? [];
  for (let i = 0; i < Math.min(endpoints.length, 20); i++) {
    const ep = endpoints[i];
    const id = `ep:${ep.method}:${ep.path}`;
    add({ id, type: "APIEndpoint", name: `${ep.method} ${ep.path}` });
  }

  // DB entities + relationships
  for (const entity of result.database_report?.entities ?? []) {
    const id = `db:${entity.name}`;
    add({ id, type: "DBTable", name: entity.name });
    for (const rel of entity.relationships ?? []) {
      const relId = `db:${rel}`;
      add({ id: relId, type: "DBTable", name: rel });
      edges.push({ source_id: id, target_id: relId, relationship: "RELATES_TO" });
    }
  }

  return { nodes, edges };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const RISK_BADGE: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-300",
  high:     "bg-orange-100 text-orange-700 border-orange-300",
  medium:   "bg-yellow-100 text-yellow-700 border-yellow-300",
  low:      "bg-green-100 text-green-700 border-green-300",
  unknown:  "bg-slate-100 text-slate-600 border-slate-300",
};

const SEV_ICON: Record<string, React.ReactNode> = {
  critical: <XCircle size={14} className="text-red-500 shrink-0" />,
  high:     <AlertTriangle size={14} className="text-orange-500 shrink-0" />,
  medium:   <AlertTriangle size={14} className="text-yellow-500 shrink-0" />,
  low:      <CheckCircle size={14} className="text-green-500 shrink-0" />,
  info:     <CheckCircle size={14} className="text-blue-400 shrink-0" />,
};

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ResultsPage() {
  const { repoId }  = useParams<{ repoId: string }>();
  const navigate    = useNavigate();
  const [tab, setTab] = useState<Tab>("overview");

  const { data: statusData } = useQuery({
    queryKey: ["repo-analysis-status", repoId],
    queryFn:  () => getRepoAnalysisStatus(repoId!),
    enabled:  !!repoId,
  });

  const analysisId = statusData?.id;
  const [pdfLoading, setPdfLoading] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);

  const handleReanalyze = useCallback(async () => {
    if (!repoId) return;
    setReanalyzing(true);
    try {
      const res = await reanalyzeRepository(repoId);
      toast.success("Re-analysis queued! Redirecting to progress…");
      navigate(`/analysis/${res.analysis_id}`);
    } catch {
      toast.error("Failed to queue re-analysis. Please try again.");
      setReanalyzing(false);
    }
  }, [repoId, navigate]);

  const handlePdfExport = useCallback(async () => {
    if (!analysisId) return;
    setPdfLoading(true);
    try {
      const res = await fetch(`/api/v1/analysis/${analysisId}/export/pdf`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        toast.error(body?.detail ?? "PDF export failed. Use JSON export instead.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${analysisId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("PDF export unavailable. Use JSON export instead.");
    } finally {
      setPdfLoading(false);
    }
  }, [analysisId]);

  const { data: result, isLoading } = useQuery<AnalysisResult>({
    queryKey: ["analysis-result", analysisId],
    queryFn:  () => getAnalysisResult(analysisId!),
    enabled:  !!analysisId && statusData?.status === "completed",
  });

  if (isLoading || !result) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <Loader2 size={32} className="animate-spin text-indigo-500 mx-auto" />
          <p className="text-sm text-slate-400">Loading analysis…</p>
        </div>
      </div>
    );
  }

  const endpointCount = result.api_report?.endpoints?.length ?? 0;
  const entityCount   = result.database_report?.entities?.length ?? 0;
  const findingCount  = result.security_report?.findings?.length ?? 0;
  const diagramCount  = result.diagrams
    ? Object.values(result.diagrams).filter(Boolean).length
    : 0;
  const secRisk = result.security_report?.overall_risk ?? "unknown";
  const { nodes: kgNodes, edges: kgEdges } = buildKnowledgeGraph(result);

  const TABS: { id: Tab; label: string; icon: React.ElementType; badge?: number | string }[] = [
    { id: "overview",  label: "Overview",     icon: Building2 },
    { id: "api",       label: "API",          icon: Zap,       badge: endpointCount  },
    { id: "database",  label: "Database",     icon: Database,  badge: entityCount    },
    { id: "security",  label: "Security",     icon: Shield,    badge: findingCount   },
    { id: "diagrams",  label: "Diagrams",     icon: GitGraph,  badge: diagramCount   },
    { id: "docs",      label: "Docs",         icon: FileText  },
    { id: "graph",     label: "Graph",        icon: Network,   badge: kgNodes.length },
    { id: "chat",      label: "Chat",         icon: MessageSquare },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* ── Header ── */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft size={18} />
          </button>

          <div className="flex-1 min-w-0">
            <h1 className="font-semibold text-slate-800 truncate">
              {result.executive_summary?.split("\n")[0]?.replace(/^#+ /, "") ?? "Repository Analysis"}
            </h1>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              {result.architecture?.style && (
                <span className="text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full font-medium">
                  {result.architecture.style.replace(/_/g, " ")}
                </span>
              )}
              {result.tech_stack && Object.entries(result.tech_stack)
                .filter(([k]) => !["languages", "frameworks", "libraries", "build_tools", "other"].includes(k))
                .slice(0, 4)
                .map(([, v]) => (
                  <span key={String(v)} className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                    {String(v)}
                  </span>
                ))}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleReanalyze}
              disabled={reanalyzing}
              title="Queue a fresh analysis for this repository"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 border border-slate-200 hover:bg-slate-50 disabled:opacity-60 transition-colors"
            >
              {reanalyzing
                ? <Loader2 size={13} className="animate-spin" />
                : <RefreshCw size={13} />
              }
              Re-analyze
            </button>
            {analysisId && (
              <>
                <a
                  href={exportJson(analysisId)}
                  download
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 border border-slate-200 hover:bg-slate-50 transition-colors"
                >
                  <Download size={13} /> JSON
                </a>
                <button
                  onClick={handlePdfExport}
                  disabled={pdfLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 transition-colors"
                >
                  {pdfLoading
                    ? <Loader2 size={13} className="animate-spin" />
                    : <Download size={13} />
                  }
                  PDF
                </button>
              </>
            )}
          </div>
        </div>

        {/* ── Stats bar ── */}
        <div className="max-w-7xl mx-auto px-4 pb-3 flex gap-6 text-sm">
          <Stat icon={<Code2 size={14} />} label="Endpoints" value={endpointCount} />
          <Stat icon={<Database size={14} />} label="Entities" value={entityCount} />
          <Stat icon={<GitGraph size={14} />} label="Diagrams" value={diagramCount} />
          <Stat
            icon={<Shield size={14} />}
            label="Risk"
            value={secRisk.toUpperCase()}
            valueClass={
              secRisk === "critical" ? "text-red-600" :
              secRisk === "high"     ? "text-orange-500" :
              secRisk === "medium"   ? "text-yellow-600" :
              secRisk === "low"      ? "text-green-600"  : "text-slate-500"
            }
          />
        </div>

        {/* ── Tabs ── */}
        <nav className="max-w-7xl mx-auto px-4 flex gap-0.5 border-t border-slate-100 overflow-x-auto">
          {TABS.map(({ id, label, icon: Icon, badge }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`relative flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium whitespace-nowrap transition-colors ${
                tab === id
                  ? "text-indigo-600"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <Icon size={15} />
              {label}
              {badge !== undefined && badge !== 0 && (
                <span className={`ml-1 text-xs px-1.5 py-0.5 rounded-full font-semibold ${
                  tab === id ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-500"
                }`}>
                  {badge}
                </span>
              )}
              {tab === id && (
                <motion.div
                  layoutId="results-tab-underline"
                  className="absolute left-0 right-0 -bottom-px h-0.5 bg-indigo-600 rounded-full"
                  transition={{ type: "spring", stiffness: 500, damping: 36 }}
                />
              )}
            </button>
          ))}
        </nav>
      </header>

      {/* ── Content ── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
          >
            {tab === "overview"  && <OverviewTab  result={result} />}
            {tab === "api"       && <APITab       result={result} />}
            {tab === "database"  && <DatabaseTab  result={result} />}
            {tab === "security"  && <SecurityTab  result={result} />}
            {tab === "diagrams"  && result.diagrams && (
              <div className="bg-white border border-slate-200 rounded-xl shadow-card p-6">
                <DiagramViewer diagrams={result.diagrams} />
              </div>
            )}
            {tab === "docs" && (
              <div className="h-[680px]">
                <DocumentationViewer
                  docs={result.markdown_docs}
                  executiveSummary={result.executive_summary}
                  analysisId={result.id}
                />
              </div>
            )}
            {tab === "graph" && repoId && (
              <GraphViewer
                repositoryId={repoId}
                fallbackNodes={kgNodes}
                fallbackEdges={kgEdges}
              />
            )}
            {tab === "chat"  && repoId && <ChatInterface repositoryId={repoId} />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Stat({ icon, label, value, valueClass = "text-slate-700" }: {
  icon: React.ReactNode; label: string; value: string | number; valueClass?: string;
}) {
  return (
    <div className="flex items-center gap-1.5 text-slate-400">
      {icon}
      <span>{label}:</span>
      <span className={`font-semibold ${valueClass}`}>{value}</span>
    </div>
  );
}

function OverviewTab({ result }: { result: AnalysisResult }) {
  const arch = result.architecture;
  return (
    <div className="space-y-5">
      {/* Executive summary */}
      {result.executive_summary && (
        <Card title="Executive Summary">
          <div className="prose prose-sm max-w-none text-slate-600 leading-relaxed whitespace-pre-wrap">
            {result.executive_summary.replace(/^#.+\n/, "").trim()}
          </div>
        </Card>
      )}

      {/* Tech stack */}
      {result.tech_stack && (
        <Card title="Tech Stack">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(result.tech_stack)
              .filter(([, v]) => v && (typeof v === "string" ? v !== "" : (v as string[]).length > 0))
              .map(([k, v]) => (
                <div key={k} className="flex flex-col gap-0.5">
                  <span className="text-xs text-slate-400 uppercase tracking-wide">{k.replace(/_/g, " ")}</span>
                  <span className="text-sm font-medium text-slate-700">
                    {Array.isArray(v) ? v.slice(0, 3).join(", ") : String(v)}
                  </span>
                </div>
              ))}
          </div>
        </Card>
      )}

      {/* Architecture */}
      {arch && (
        <Card title={`Architecture — ${arch.style.replace(/_/g, " ")}`}>
          <p className="text-sm text-slate-600 mb-4">{arch.description}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {arch.layers.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Layers</p>
                <ul className="space-y-1.5">
                  {arch.layers.map((l, i) => (
                    <li key={i} className="text-sm text-slate-600 flex gap-2">
                      <ChevronRight size={14} className="text-indigo-400 shrink-0 mt-0.5" />
                      <span><strong className="text-slate-700">{l.name}</strong> — {l.description}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {arch.patterns.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Design Patterns</p>
                <div className="flex flex-wrap gap-2">
                  {arch.patterns.map((p, i) => (
                    <span key={i} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium">{p}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
          {arch.concerns.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Concerns</p>
              <ul className="space-y-1">
                {arch.concerns.map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <AlertTriangle size={13} className="text-yellow-500 shrink-0 mt-0.5" /> {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Module breakdown */}
      {result.module_breakdown.length > 0 && (
        <Card title="Module Breakdown">
          <div className="divide-y divide-slate-100">
            {result.module_breakdown.map((m, i) => (
              <div key={i} className="py-3 first:pt-0 last:pb-0">
                <div className="flex items-start gap-2">
                  <span className="font-semibold text-sm text-slate-800">{m.module}</span>
                  {m.public_interfaces?.length > 0 && (
                    <div className="flex flex-wrap gap-1 ml-2">
                      {m.public_interfaces.slice(0, 4).map((ifc: string, j: number) => (
                        <code key={j} className="text-xs text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">{ifc}</code>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{m.responsibility}</p>
                {m.dependencies?.length > 0 && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    Depends on: {m.dependencies.slice(0, 5).join(", ")}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function APITab({ result }: { result: AnalysisResult }) {
  const api = result.api_report;
  if (!api) return <Empty message="No API report available." />;
  return (
    <div className="space-y-5">
      <Card title="API Overview">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <InfoCell label="Type"           value={api.type}                    />
          <InfoCell label="Authentication" value={api.authentication ?? "—"}   />
          <InfoCell label="Versioning"     value={api.versioning ?? "—"}       />
          <InfoCell label="Base Path"      value={api.base_path ?? "/"}        />
        </div>
      </Card>

      {api.endpoints.length > 0 && (
        <Card title={`Endpoints (${api.endpoints.length})`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-400 uppercase tracking-wide">
                  <th className="text-left py-2 pr-3">Method</th>
                  <th className="text-left py-2 pr-3">Path</th>
                  <th className="text-left py-2 pr-3">Summary</th>
                  <th className="text-left py-2">Auth</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {api.endpoints.map((ep, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="py-2 pr-3">
                      <span className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                        ep.method === "GET"    ? "bg-blue-50 text-blue-700"   :
                        ep.method === "POST"   ? "bg-green-50 text-green-700" :
                        ep.method === "PUT"    ? "bg-yellow-50 text-yellow-700" :
                        ep.method === "DELETE" ? "bg-red-50 text-red-700"    :
                        "bg-slate-100 text-slate-700"
                      }`}>{ep.method}</span>
                    </td>
                    <td className="py-2 pr-3 font-mono text-xs text-slate-700">{ep.path}</td>
                    <td className="py-2 pr-3 text-slate-600">{ep.summary}</td>
                    <td className="py-2">
                      {ep.auth_required
                        ? <Lock size={13} className="text-indigo-500" />
                        : <span className="text-slate-300 text-xs">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {api.services && api.services.length > 0 && (
        <Card title="Services">
          <div className="grid gap-3 sm:grid-cols-2">
            {api.services.map((s, i) => (
              <div key={i} className="p-3 bg-slate-50 rounded-lg">
                <p className="font-semibold text-sm text-slate-800">{s.name}</p>
                <p className="text-xs text-slate-500 mt-0.5">{s.responsibility}</p>
                {s.methods?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {s.methods.slice(0, 6).map((m: string, j: number) => (
                      <code key={j} className="text-xs text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">{m}()</code>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function DatabaseTab({ result }: { result: AnalysisResult }) {
  const db = result.database_report;
  if (!db) return <Empty message="No database report available." />;
  return (
    <div className="space-y-5">
      <Card title="Database Overview">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <InfoCell label="ORM"        value={db.orm ?? "—"}          />
          <InfoCell label="Database"   value={db.database_type ?? "—"} />
          <InfoCell label="Migrations" value={db.migrations_present ? "Yes" : "No"} />
        </div>
      </Card>

      {db.entities.length > 0 && (
        <Card title={`Entities (${db.entities.length})`}>
          <div className="space-y-4">
            {db.entities.map((entity, i) => (
              <div key={i} className="border border-slate-100 rounded-lg overflow-hidden">
                <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                  <span className="font-semibold text-sm text-slate-800">{entity.name}</span>
                  {entity.relationships.length > 0 && (
                    <span className="text-xs text-slate-400">{entity.relationships.slice(0, 3).join(", ")}</span>
                  )}
                </div>
                {entity.columns.length > 0 && (
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-50">
                        <th className="text-left px-4 py-1.5 text-slate-400 font-medium">Column</th>
                        <th className="text-left px-4 py-1.5 text-slate-400 font-medium">Type</th>
                        <th className="text-left px-4 py-1.5 text-slate-400 font-medium">Nullable</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entity.columns.map((col, j) => (
                        <tr key={j} className="border-t border-slate-50 hover:bg-slate-50">
                          <td className="px-4 py-1.5 font-mono text-slate-700">{col.name}</td>
                          <td className="px-4 py-1.5 text-indigo-600">{col.type}</td>
                          <td className="px-4 py-1.5 text-slate-500">{col.nullable}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function SecurityTab({ result }: { result: AnalysisResult }) {
  const sec = result.security_report;
  if (!sec) return <Empty message="No security report available." />;
  const risk = sec.overall_risk?.toLowerCase() ?? "unknown";
  return (
    <div className="space-y-5">
      <Card title="Security Posture">
        <div className="flex items-center gap-3 mb-4">
          <span className={`text-sm font-bold px-3 py-1 rounded-full border ${RISK_BADGE[risk] ?? RISK_BADGE.unknown}`}>
            {risk.toUpperCase()} RISK
          </span>
        </div>
        <p className="text-sm text-slate-600">{sec.summary}</p>
        {(sec.authentication_analysis || sec.authorization_analysis) && (
          <div className="mt-4 grid sm:grid-cols-2 gap-4">
            {sec.authentication_analysis && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Authentication</p>
                <p className="text-sm text-slate-600">{sec.authentication_analysis}</p>
              </div>
            )}
            {sec.authorization_analysis && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Authorization</p>
                <p className="text-sm text-slate-600">{sec.authorization_analysis}</p>
              </div>
            )}
          </div>
        )}
      </Card>

      {sec.findings.length > 0 && (
        <Card title={`Findings (${sec.findings.length})`}>
          <div className="space-y-3">
            {sec.findings.map((f, i) => (
              <div key={i} className={`p-4 rounded-lg border ${RISK_BADGE[f.severity] ?? RISK_BADGE.unknown}`}>
                <div className="flex items-start gap-2">
                  {SEV_ICON[f.severity] ?? SEV_ICON.info}
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm">{f.category}</p>
                    <p className="text-sm opacity-80 mt-0.5">{f.description}</p>
                    {f.file_path && (
                      <code className="text-xs mt-1 block opacity-70">
                        {f.file_path}{f.line_number ? `:${f.line_number}` : ""}
                      </code>
                    )}
                    <p className="text-xs mt-2 font-medium opacity-90">
                      Fix: {f.recommendation}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Shared micro-components ───────────────────────────────────────────────────

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-card p-5">
      <h2 className="font-semibold text-slate-800 mb-4 capitalize">{title}</h2>
      {children}
    </div>
  );
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-400 uppercase tracking-wide">{label}</p>
      <p className="text-sm font-medium text-slate-700 mt-0.5">{value}</p>
    </div>
  );
}

function Empty({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-48 text-slate-400 text-sm bg-white border border-slate-200 rounded-xl">
      {message}
    </div>
  );
}
