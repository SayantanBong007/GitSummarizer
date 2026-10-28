import { useEffect, useRef, useState } from "react";
import type { StepEvent } from "@/types";

export type StreamStatus = "connecting" | "running" | "completed" | "failed" | "idle";

export interface StreamState {
  events: StepEvent[];
  streamStatus: StreamStatus;
  progress: number;
  currentStep: string | null;
  errorMessage: string | null;
}

export function useAnalysisStream(analysisId: string | null): StreamState {
  const [state, setState] = useState<StreamState>({
    events: [],
    streamStatus: "idle",
    progress: 0,
    currentStep: null,
    errorMessage: null,
  });

  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!analysisId) return;

    const es = new EventSource(`/api/v1/analysis/${analysisId}/stream`);
    esRef.current = es;

    setState((prev) => ({ ...prev, streamStatus: "connecting" }));

    es.addEventListener("step", (e: MessageEvent) => {
      const event: StepEvent = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        streamStatus: "running",
        progress: event.progress,
        currentStep: event.step,
        // Replace existing event for same step (idempotent replay)
        events: [
          ...prev.events.filter((ev) => ev.step !== event.step),
          event,
        ],
      }));
    });

    es.addEventListener("done", () => {
      setState((prev) => ({
        ...prev,
        streamStatus: "completed",
        progress: 1.0,
        currentStep: "done",
      }));
      es.close();
    });

    es.addEventListener("error", (e: MessageEvent) => {
      let message = "Analysis failed.";
      try {
        const data = JSON.parse(e.data);
        if (data.message) message = data.message;
      } catch {
        // ignore parse errors on the error event itself
      }
      setState((prev) => ({ ...prev, streamStatus: "failed", errorMessage: message }));
      es.close();
    });

    // SSE connection error (network/server down) — browser will auto-reconnect
    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        setState((prev) => {
          if (prev.streamStatus === "completed" || prev.streamStatus === "failed") return prev;
          return { ...prev, streamStatus: "failed", errorMessage: "Connection lost." };
        });
      }
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [analysisId]);

  return state;
}
