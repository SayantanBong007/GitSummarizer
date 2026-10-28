"""
Model routing — all agents share a fallback-chained LLM (primary → fallback_1 → fallback_2).

Default chain (via LangChain .with_fallbacks):
  1. openai/gpt-oss-120b:free          ← GPT OSS 120B (primary)
  2. meta-llama/llama-3.3-70b-instruct:free ← Llama 3.3 70B (fallback 1)
  3. qwen/qwen3-coder:free             ← Qwen3 Coder (fallback 2)

All models are free-tier on OpenRouter — only OPENROUTER_API_KEY is needed.
Override any model ID via env vars: OPENROUTER_MODEL / OPENROUTER_FALLBACK_1 / OPENROUTER_FALLBACK_2
"""
from enum import StrEnum

from langchain_core.language_models import BaseChatModel

from backend.llm.client import get_llm_with_fallbacks


class TaskType(StrEnum):
    CLASSIFY = "classify"    # quick yes/no or label tasks
    SUMMARIZE = "summarize"  # medium output
    ANALYZE = "analyze"      # deep analysis, long output
    GENERATE = "generate"    # code / diagram generation
    CHAT = "chat"            # interactive RAG chat


_TEMPERATURE: dict[TaskType, float] = {
    TaskType.CLASSIFY: 0.0,
    TaskType.SUMMARIZE: 0.2,
    TaskType.ANALYZE: 0.1,
    TaskType.GENERATE: 0.3,
    TaskType.CHAT: 0.5,
}

_MAX_TOKENS: dict[TaskType, int] = {
    TaskType.CLASSIFY: 512,
    TaskType.SUMMARIZE: 1500,
    TaskType.ANALYZE: 2000,   # Groq free tier: 12k TPM; prompt ~6-8k + 2k output fits
    TaskType.GENERATE: 2000,
    TaskType.CHAT: 2000,
}


class ModelRouter:
    """Routes tasks to a fallback-chained LLM (primary → fallback_1 → fallback_2)."""

    def get(self, task: TaskType, **kwargs: object) -> BaseChatModel:
        return get_llm_with_fallbacks(
            temperature=float(kwargs.get("temperature", _TEMPERATURE[task])),
            max_tokens=int(kwargs.get("max_tokens", _MAX_TOKENS[task])),
        )


_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
