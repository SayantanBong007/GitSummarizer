import { useState, useCallback } from "react";
import { chatWithRepo } from "@/api/client";
import type { ChatMessage, ChatSource } from "@/types";

interface ChatState {
  messages: ChatMessage[];
  sources: ChatSource[];
  loading: boolean;
  error: string | null;
}

export function useChat(repositoryId: string) {
  const [state, setState] = useState<ChatState>({
    messages: [],
    sources: [],
    loading: false,
    error: null,
  });

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: ChatMessage = { role: "user", content };
      const updatedMessages = [...state.messages, userMessage];

      setState((s) => ({
        ...s,
        messages: updatedMessages,
        loading: true,
        error: null,
      }));

      try {
        const response = await chatWithRepo(repositoryId, updatedMessages);
        setState((s) => ({
          ...s,
          messages: [...updatedMessages, response.message],
          sources: response.sources,
          loading: false,
        }));
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setState((s) => ({
          ...s,
          loading: false,
          error: detail ?? (err instanceof Error ? err.message : "Chat request failed"),
        }));
      }
    },
    [repositoryId, state.messages]
  );

  const clearMessages = useCallback(() => {
    setState({ messages: [], sources: [], loading: false, error: null });
  }, []);

  return { ...state, sendMessage, clearMessages };
}
