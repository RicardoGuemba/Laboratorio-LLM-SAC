from __future__ import annotations

import random
import re

from backend.debate.casual_prompts import FALLBACK_TOPICS, build_topic_generation_messages
from backend.debate.session import DebateSession, DebaterId
from backend.llm.lmstudio import LMStudioClient


def _clean_topic(raw: str) -> str:
    text = raw.strip().strip("\"'`""''«»")
    text = re.sub(r"^(Tema|Assunto|Topic)\s*[:：]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 200:
        text = text[:200].rsplit(" ", 1)[0] + "…"
    return text


def _is_valid_topic(text: str) -> bool:
    if len(text) < 8 or len(text) > 200:
        return False
    lower = text.lower()
    invalid_markers = (
        "the user",
        "let's",
        "okay,",
        "respond as",
        "specified persona",
        "tackle this",
        "they provided",
        "as prof.",
        "as prof ",
        "phd with",
    )
    if any(marker in lower for marker in invalid_markers):
        return False
    pt_hint = sum(1 for ch in "ãõáéíóúçâê" if ch in lower)
    en_hint = sum(1 for word in (" the ", " and ", " with ", " this ", " user ") if word in lower)
    if en_hint >= 2 and pt_hint == 0:
        return False
    return True


async def generate_casual_topic(
    lm_client: LMStudioClient,
    session: DebateSession,
    starter: DebaterId,
) -> str:
    profile_key = session.rico_profile if starter == DebaterId.RICO else session.pobre_profile
    skill_ids = session.rico_skills if starter == DebaterId.RICO else session.pobre_skills
    model = session.rico_model if starter == DebaterId.RICO else session.pobre_model
    generation_overrides = (
        session.rico_llm_params if starter == DebaterId.RICO else session.pobre_llm_params
    )
    messages = build_topic_generation_messages(starter, profile_key, skill_ids)
    try:
        content, reasoning = await lm_client.complete_non_stream(
            starter.value,
            messages,
            thinking=False,
            model=model,
            profile_key=profile_key,
            generation_overrides={
                **generation_overrides,
                "max_tokens": min(int(generation_overrides.get("max_tokens", 256)), 80),
                "temperature": float(generation_overrides.get("temperature", 0.8)),
            },
        )
        candidate = _clean_topic(content or reasoning)
        if _is_valid_topic(candidate):
            return candidate
    except Exception:
        pass
    return random.choice(FALLBACK_TOPICS)


def pick_topic_starter() -> DebaterId:
    return random.choice([DebaterId.RICO, DebaterId.POBRE])
