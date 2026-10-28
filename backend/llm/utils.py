from __future__ import annotations

import json
import re


def extract_json(raw: str) -> dict:
    """
    Robustly extract a JSON object from an LLM response.

    Handles the three most common failure modes from free-tier models:
      1. <think>...</think> reasoning blocks  (DeepSeek R1, Qwen3, Nemotron)
      2. Markdown code fences  (```json ... ```)
      3. Prose before/after the JSON object
    """
    # 1. Strip reasoning blocks produced by chain-of-thought models
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)

    # 2. Try to pull JSON out of the first markdown code fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Strip any remaining fence markers and try a direct parse
    text = re.sub(r"```(?:json)?", "", text)
    text = text.replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4. Extract the outermost { ... } object — handles prose before/after JSON
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON object found in LLM response: {raw[:300]!r}")
