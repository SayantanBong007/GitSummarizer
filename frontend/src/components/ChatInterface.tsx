import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { Send, Bot, User, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useChat } from "@/hooks/useChat";

interface Props {
  repositoryId: string;
}

export default function ChatInterface({ repositoryId }: Props) {
  const { messages, sources, loading, error, sendMessage } = useChat(repositoryId);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    await sendMessage(text);
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[560px] bg-white border border-slate-200 rounded-xl shadow-card overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
        <p className="text-sm font-medium text-slate-700">Chat with Repository</p>
        <p className="text-xs text-slate-400">Ask anything about the codebase</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 text-sm py-8">
            <Bot size={32} className="mx-auto mb-2 opacity-40" />
            <p>Ask about the architecture, APIs, database schema, or any part of the code.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <div className={`p-2 rounded-full shrink-0 ${msg.role === "user" ? "bg-indigo-100" : "bg-slate-100"}`}>
              {msg.role === "user" ? <User size={16} className="text-indigo-600" /> : <Bot size={16} className="text-slate-600" />}
            </div>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-50 text-slate-800 border border-slate-200"
              }`}
            >
              {msg.role === "assistant" ? (
                <ReactMarkdown className="prose prose-sm max-w-none">{msg.content}</ReactMarkdown>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          </motion.div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="p-2 rounded-full bg-slate-100">
              <Bot size={16} className="text-slate-600" />
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3">
              <Loader2 size={16} className="animate-spin text-slate-400" />
            </div>
          </div>
        )}
        {error && (
          <p className="text-red-500 text-xs text-center">{error}</p>
        )}
        <div ref={bottomRef} />
      </div>

      {sources.length > 0 && (
        <div className="px-4 py-2 border-t border-slate-100 bg-slate-50">
          <p className="text-xs text-slate-400 mb-1">Sources:</p>
          <div className="flex flex-wrap gap-1">
            {sources.map((s, i) => (
              <span key={i} className="text-xs bg-white border border-slate-200 rounded px-2 py-0.5 text-slate-600">
                {s.file?.split("/").pop()} {s.symbol ? `· ${s.symbol}` : ""}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="p-3 border-t border-slate-100">
        <div className="flex items-end gap-2 bg-slate-50 border border-slate-200 rounded-xl p-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about the codebase… (Enter to send)"
            rows={1}
            className="flex-1 bg-transparent outline-none text-sm text-slate-800 placeholder-slate-400 resize-none max-h-32"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white rounded-lg transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
