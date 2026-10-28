import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { GitBranch, Search, Loader2 } from "lucide-react";
import { submitRepository } from "@/api/client";
import { toast } from "sonner";

export default function RepositoryForm() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed.startsWith("https://github.com/")) {
      toast.error("Please enter a valid GitHub URL (https://github.com/owner/repo)");
      return;
    }

    setLoading(true);
    try {
      const result = await submitRepository(trimmed);
      toast.success("Repository submitted — analysis started!");
      navigate(`/analysis/${result.analysis_id}?repo=${result.repository_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Submission failed";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-2xl mx-auto"
    >
      <div
        className="flex items-center gap-2 bg-white border border-slate-200 rounded-2xl shadow-glow p-2
                   transition-shadow focus-within:ring-2 focus-within:ring-indigo-500/30 focus-within:border-indigo-300"
      >
        <GitBranch className="ml-3 text-slate-400 shrink-0" size={20} />
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repository"
          className="flex-1 px-3 py-3 text-slate-800 placeholder-slate-400 bg-transparent outline-none text-base"
          disabled={loading}
          aria-label="GitHub repository URL"
        />
        <motion.button
          type="submit"
          disabled={loading || !url.trim()}
          whileHover={{ scale: loading ? 1 : 1.02 }}
          whileTap={{ scale: loading ? 1 : 0.97 }}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600
                     text-white px-5 py-3 rounded-xl font-medium transition-colors shrink-0"
        >
          {loading ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Search size={18} />
          )}
          {loading ? "Submitting…" : "Analyze"}
        </motion.button>
      </div>
    </form>
  );
}
