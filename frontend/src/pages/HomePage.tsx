import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  GitBranch, CheckCircle2, XCircle, Clock,
  Zap, Shield, GitGraph, MessageSquare, FileText, Database,
  ArrowRight,
} from "lucide-react";
import RepositoryForm from "@/components/RepositoryForm";
import { listRepositories } from "@/api/client";

const STATUS_ICON = {
  cloned:  <CheckCircle2 size={14} className="text-emerald-500" />,
  error:   <XCircle      size={14} className="text-red-500"    />,
  pending: <Clock        size={14} className="text-slate-400"  />,
  cloning: <Clock        size={14} className="text-indigo-400 animate-pulse" />,
};

const FEATURES = [
  {
    icon: Zap,
    color: "text-indigo-600 bg-indigo-50",
    title: "5 Parallel Agents",
    desc: "Architecture, API, frontend, database, and security agents run concurrently with LangGraph orchestration.",
  },
  {
    icon: GitGraph,
    color: "text-violet-600 bg-violet-50",
    title: "Auto-generated Diagrams",
    desc: "Mermaid flowcharts, class diagrams, ER diagrams, and sequence flows from Tree-sitter AST parsing.",
  },
  {
    icon: Shield,
    color: "text-rose-600 bg-rose-50",
    title: "Security Audit",
    desc: "OWASP-aligned findings with severity ratings, file locations, and actionable recommendations.",
  },
  {
    icon: Database,
    color: "text-emerald-600 bg-emerald-50",
    title: "Database Schema",
    desc: "Entity extraction, column types, relationships, migration detection across all major ORMs.",
  },
  {
    icon: FileText,
    color: "text-amber-600 bg-amber-50",
    title: "Full Documentation",
    desc: "Executive summary, onboarding guide, architecture docs, and API reference — export to JSON or PDF.",
  },
  {
    icon: MessageSquare,
    color: "text-sky-600 bg-sky-50",
    title: "AI Chat",
    desc: "Ask any question about the codebase and get context-aware answers backed by vector search.",
  },
];

export default function HomePage() {
  const navigate = useNavigate();
  const { data } = useQuery({
    queryKey: ["repositories"],
    queryFn:  () => listRepositories(),
    refetchInterval: 10_000,
  });

  return (
    <div className="min-h-screen bg-white">
      {/* ── Nav ── */}
      <nav className="border-b border-slate-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-slate-800">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center shadow-glow">
              <GitBranch size={15} className="text-white" />
            </div>
            <span className="tracking-tight">GitSummarize</span>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4">
        {/* ── Hero ── */}
        <motion.div
          className="relative text-center pt-24 pb-14"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          {/* Subtle dot-grid + radial fade behind the hero */}
          <div
            className="pointer-events-none absolute inset-x-0 -top-4 h-[420px] bg-dot-grid bg-dots"
            style={{
              maskImage: "radial-gradient(ellipse 60% 100% at 50% 0%, black 40%, transparent 80%)",
              WebkitMaskImage: "radial-gradient(ellipse 60% 100% at 50% 0%, black 40%, transparent 80%)",
            }}
          />

          <div className="relative inline-flex items-center gap-2 bg-indigo-50 border border-indigo-100 text-indigo-700 px-4 py-1.5 rounded-full text-sm font-medium mb-7">
            <Zap size={14} />
            Agentic Repository Analysis
          </div>
          <h1 className="relative text-5xl sm:text-6xl font-extrabold text-slate-900 leading-[1.1] mb-5 tracking-tight">
            Understand any codebase
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-500">
              in under 5 minutes
            </span>
          </h1>
          <p className="relative text-xl text-slate-500 max-w-2xl mx-auto mb-10 leading-relaxed">
            Paste a public GitHub URL and get professional architecture documentation,
            interactive diagrams, a security audit, and an AI assistant — fully automated.
          </p>

          {/* Form */}
          <div className="relative max-w-2xl mx-auto">
            <RepositoryForm />
          </div>

          <p className="relative mt-4 text-xs text-slate-400">
            Works with any public GitHub repository · No login required
          </p>
        </motion.div>

        {/* ── Features ── */}
        <div className="py-14 border-t border-slate-100">
          <h2 className="text-center text-sm font-semibold text-slate-400 uppercase tracking-widest mb-8">
            What you get
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(({ icon: Icon, color, title, desc }, i) => (
              <motion.div
                key={title}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.4, delay: i * 0.06, ease: "easeOut" }}
                whileHover={{ y: -3 }}
                className="p-5 bg-white border border-slate-100 rounded-2xl shadow-card hover:shadow-card-hover hover:border-slate-200 transition-shadow"
              >
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-3 ${color}`}>
                  <Icon size={18} />
                </div>
                <h3 className="font-semibold text-slate-800 mb-1">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* ── Recent repos ── */}
        {data && data.items.length > 0 && (
          <div className="py-10 border-t border-slate-100">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-4">
              Recent Analyses
            </h2>
            <div className="grid gap-2 sm:grid-cols-2">
              {data.items.map((repo) => (
                <motion.button
                  key={repo.id}
                  onClick={() => navigate(`/results/${repo.id}`)}
                  whileHover={{ y: -2 }}
                  whileTap={{ scale: 0.99 }}
                  className="flex items-center gap-3 p-4 bg-white border border-slate-200 rounded-xl
                             hover:border-indigo-300 shadow-card hover:shadow-card-hover transition-shadow text-left group"
                >
                  {STATUS_ICON[repo.clone_status] ?? STATUS_ICON.pending}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">
                      {repo.owner}/{repo.name}
                    </p>
                    {repo.description && (
                      <p className="text-xs text-slate-400 truncate mt-0.5">{repo.description}</p>
                    )}
                    {repo.languages && repo.languages.length > 0 && (
                      <div className="flex gap-1 mt-1.5">
                        {repo.languages.slice(0, 4).map((lang) => (
                          <span key={lang} className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">
                            {lang}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <ArrowRight
                    size={16}
                    className="text-slate-300 group-hover:text-indigo-500 transition-colors shrink-0"
                  />
                </motion.button>
              ))}
            </div>
          </div>
        )}

        {/* ── Footer ── */}
        <footer className="py-8 border-t border-slate-100 text-center text-xs text-slate-400">
          GitSummarize · Built with FastAPI, LangGraph, Tree-sitter, and React
        </footer>
      </div>
    </div>
  );
}
