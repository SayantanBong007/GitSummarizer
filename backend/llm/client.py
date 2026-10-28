from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from backend.config import get_settings


def _make_groq(model: str, temperature: float, max_tokens: int) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        openai_api_key=settings.groq_api_key,
        openai_api_base=settings.groq_base_url,
        max_retries=1,
        # The openai/gpt-oss-* models are reasoning models: they spend part of
        # max_tokens on an internal chain-of-thought before the real answer, which
        # can truncate the JSON response before it's complete (observed live: a
        # security_agent response cut off mid-word after exhausting max_tokens).
        # "low" keeps reasoning short so the actual answer reliably fits.
        reasoning_effort="low",
    )


def get_llm(
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> BaseChatModel:
    """Return the primary LLM (no fallbacks). Use get_llm_with_fallbacks() for agents."""
    settings = get_settings()
    return _make_groq(
        model=model or settings.groq_model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_fast_llm(temperature: float = 0.1, max_tokens: int = 1500) -> ChatOpenAI:
    """
    Fast 8b model for context-heavy agents (backend/frontend/database/security).
    Uses llama-3.1-8b-instant on a separate TPM quota from the 70b model.
    max_retries=5 lets the OpenAI client respect Groq's Retry-After header and
    wait through TPM window resets (~60s) rather than failing immediately.
    """
    settings = get_settings()
    return ChatOpenAI(
        model=settings.groq_fallback_1,
        temperature=temperature,
        max_tokens=max_tokens,
        openai_api_key=settings.groq_api_key,
        openai_api_base=settings.groq_base_url,
        max_retries=5,
        reasoning_effort="low",
    )


def get_llm_with_fallbacks(
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> BaseChatModel:
    """
    Return a LangChain model chain: groq primary → groq fast → groq fallback.
    All three hit Groq's OpenAI-compatible endpoint with the same key.
    """
    from openai import InternalServerError, RateLimitError

    settings = get_settings()
    primary   = _make_groq(settings.groq_model,     temperature, max_tokens)
    fallback_1 = _make_groq(settings.groq_fallback_1, temperature, max_tokens)
    fallback_2 = _make_groq(settings.groq_fallback_2, temperature, max_tokens)
    return primary.with_fallbacks(
        [fallback_1, fallback_2],
        exceptions_to_handle=(RateLimitError, InternalServerError, Exception),
    )
