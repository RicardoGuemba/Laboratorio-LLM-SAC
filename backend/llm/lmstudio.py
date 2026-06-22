from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from backend.config import load_config
from backend.debate.llm_params import is_chat_model, merge_llm_params


class LMStudioClient:
    def __init__(self) -> None:
        self._refresh_config()

    def _refresh_config(self) -> None:
        config = load_config()
        self.base_url = config["lmstudio"]["base_url"].rstrip("/")
        self.debaters = config["lmstudio"]["debaters"]

    async def health_check(self) -> dict[str, Any]:
        self._refresh_config()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/models")
                resp.raise_for_status()
                data = resp.json()
                models = [
                    m.get("id", m.get("name", ""))
                    for m in data.get("data", [])
                    if is_chat_model(m.get("id", m.get("name", "")))
                ]
                return {"online": True, "models": models}
        except Exception as exc:
            return {"online": False, "error": str(exc), "models": []}

    async def list_models(self) -> list[str]:
        result = await self.health_check()
        return result.get("models", [])

    def get_debater_config(self, debater: str, profile_key: str | None = None) -> dict[str, Any]:
        return dict(self.debaters[debater])

    def default_model(self, debater: str) -> str:
        return self.get_debater_config(debater)["model"]

    def default_models(self) -> dict[str, str]:
        return {name: cfg["model"] for name, cfg in self.debaters.items()}

    def resolve_default_model(self, debater: str, available: list[str]) -> str:
        """Prefere modelo configurado; aceita qualquer LLM de chat disponível."""
        cfg = self.get_debater_config(debater)
        preferred = cfg.get("model", "")
        family = (cfg.get("model_family") or "").lower()
        chat_models = [m for m in available if is_chat_model(m)]

        if not chat_models:
            return preferred
        if preferred in chat_models:
            return preferred

        if family:
            matches = [m for m in chat_models if family in m.lower()]
            if matches:
                pref_slug = preferred.split("/")[-1].lower()
                for candidate in matches:
                    if pref_slug and pref_slug in candidate.lower():
                        return candidate
                return matches[0]

        pref_slug = preferred.split("/")[-1].lower()
        if pref_slug:
            for candidate in chat_models:
                if pref_slug in candidate.lower():
                    return candidate

        return chat_models[0]

    def resolved_defaults(self, available: list[str]) -> dict[str, str]:
        return {
            name: self.resolve_default_model(name, available)
            for name in self.debaters
        }

    def pick_model(
        self,
        override: str | None,
        debater: str,
        available: list[str],
    ) -> str:
        chat_models = [m for m in available if is_chat_model(m)] if available else []

        if override and chat_models and override in chat_models:
            return override
        if override and not chat_models:
            return override
        if override and chat_models and override not in chat_models:
            raise ValueError(
                f"Modelo '{override}' não está carregado no LM Studio. "
                f"Modelos disponíveis: {', '.join(chat_models)}"
            )

        resolved = self.resolve_default_model(debater, chat_models)
        if not chat_models:
            return override or resolved
        if resolved in chat_models:
            return resolved
        return chat_models[0]

    def resolve_model(self, debater: str, override: str | None) -> str:
        return override or self.default_model(debater)

    def _resolve_limits(self, cfg: dict[str, Any], thinking: bool) -> tuple[int, float]:
        if thinking:
            max_tokens = cfg.get("max_tokens_thinking", cfg.get("max_tokens", 512))
            timeout_s = cfg.get("timeout_s_thinking", cfg.get("timeout_s", 120))
        else:
            max_tokens = cfg.get("max_tokens_direct", cfg.get("max_tokens", 256))
            timeout_s = cfg.get("timeout_s_direct", cfg.get("timeout_s", 60))
        return int(max_tokens), float(timeout_s)

    def _build_payload(
        self,
        cfg: dict[str, Any],
        messages: list[dict[str, str]],
        *,
        model: str,
        thinking: bool,
        stream: bool,
        generation_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        merged = merge_llm_params(cfg, generation_overrides)
        max_tokens = int(merged["max_tokens"])
        if thinking:
            max_tokens = int(cfg.get("max_tokens_thinking", max_tokens))
        return {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": max_tokens,
            "temperature": float(merged["temperature"]),
            "top_p": float(merged["top_p"]),
        }

    async def stream_completion(
        self,
        debater: str,
        messages: list[dict[str, str]],
        *,
        thinking: bool = False,
        model: str | None = None,
        profile_key: str | None = None,
        generation_overrides: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, str], None]:
        self._refresh_config()
        cfg = self.get_debater_config(debater, profile_key)
        model_name = self.resolve_model(debater, model)
        payload = self._build_payload(
            cfg,
            messages,
            model=model_name,
            thinking=thinking,
            stream=True,
            generation_overrides=generation_overrides,
        )
        _, timeout_s = self._resolve_limits(cfg, thinking)
        timeout = httpx.Timeout(timeout_s, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    reasoning = delta.get("reasoning_content")
                    content = delta.get("content")
                    if thinking and reasoning:
                        yield {"kind": "reasoning", "text": reasoning}
                    if content:
                        yield {"kind": "content", "text": content}

    async def complete_non_stream(
        self,
        debater: str,
        messages: list[dict[str, str]],
        *,
        thinking: bool = False,
        model: str | None = None,
        profile_key: str | None = None,
        generation_overrides: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        self._refresh_config()
        cfg = self.get_debater_config(debater, profile_key)
        model_name = self.resolve_model(debater, model)
        payload = self._build_payload(
            cfg,
            messages,
            model=model_name,
            thinking=thinking,
            stream=False,
            generation_overrides=generation_overrides,
        )
        _, timeout_s = self._resolve_limits(cfg, thinking)
        timeout = httpx.Timeout(timeout_s, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            message = resp.json()["choices"][0]["message"]
            content = (message.get("content") or "").strip()
            reasoning = (message.get("reasoning_content") or "").strip()
            return content, reasoning
