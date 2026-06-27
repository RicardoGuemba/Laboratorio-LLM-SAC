from __future__ import annotations

from typing import Any

DEFAULT_LLM_PARAMS: dict[str, float | int] = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 256,
}


def merge_llm_params(
    base: dict[str, Any],
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(DEFAULT_LLM_PARAMS)
    merged["temperature"] = float(base.get("temperature", merged["temperature"]))
    merged["top_p"] = float(base.get("top_p", merged["top_p"]))
    direct = base.get("max_tokens_direct", base.get("max_tokens"))
    if direct is not None:
        merged["max_tokens"] = int(direct)
    if override:
        for key in ("temperature", "top_p", "max_tokens"):
            if override.get(key) is not None:
                merged[key] = override[key]
    return merged


def is_chat_model(model_id: str) -> bool:
    lower = model_id.lower()
    skip = ("embed", "embedding", "nomic-embed", "rerank")
    return not any(token in lower for token in skip)
