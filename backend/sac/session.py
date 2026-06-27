from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RoleId(str, Enum):
    CLIENTE = "cliente"
    SAC = "sac"


class SacStatus(str, Enum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class TurnRecord:
    id: str
    role: RoleId
    text: str
    title: str | None = None
    thinking: str | None = None
    latency_ms: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class RagChunkRef:
    doc_id: str
    section: str
    text: str
    score: float


@dataclass
class SacSession:
    id: str
    cliente_profile: str
    sac_profile: str
    cliente_model: str
    sac_model: str
    cliente_thinking: bool = False
    sac_thinking: bool = False
    cliente_skills: list[str] = field(default_factory=list)
    sac_skills: list[str] = field(default_factory=list)
    cliente_llm_params: dict[str, Any] = field(default_factory=dict)
    sac_llm_params: dict[str, Any] = field(default_factory=dict)
    status: SacStatus = SacStatus.IDLE
    complaint_title: str = ""
    complaint_text: str = ""
    response_text: str = ""
    rag_chunks: list[RagChunkRef] = field(default_factory=list)
    turns: list[TurnRecord] = field(default_factory=list)
    category: str | None = None
    current_stream_text: str = ""

    @staticmethod
    def create(
        cliente_profile: str,
        sac_profile: str,
        cliente_model: str,
        sac_model: str,
        cliente_thinking: bool = False,
        sac_thinking: bool = False,
        cliente_skills: list[str] | None = None,
        sac_skills: list[str] | None = None,
        cliente_llm_params: dict[str, Any] | None = None,
        sac_llm_params: dict[str, Any] | None = None,
    ) -> SacSession:
        from backend.personas.persona_store import get_profile, load_defaults

        defaults = load_defaults()
        cliente_defaults = defaults.get("cliente", {})
        sac_defaults = defaults.get("sac", {})

        cliente_skill_list = cliente_skills or list(
            get_profile("cliente", cliente_profile).get("default_skills")
            or cliente_defaults.get("skills", [])
        )
        sac_skill_list = sac_skills or list(
            get_profile("sac", sac_profile).get("default_skills")
            or sac_defaults.get("skills", [])
        )

        return SacSession(
            id=str(uuid.uuid4()),
            cliente_profile=cliente_profile,
            sac_profile=sac_profile,
            cliente_model=cliente_model,
            sac_model=sac_model,
            cliente_thinking=cliente_thinking,
            sac_thinking=sac_thinking,
            cliente_skills=cliente_skill_list,
            sac_skills=sac_skill_list,
            cliente_llm_params=dict(cliente_llm_params or {}),
            sac_llm_params=dict(sac_llm_params or {}),
        )

    @staticmethod
    def _profile_display_name(role: str, profile_id: str) -> str:
        from backend.personas.persona_store import get_profile

        profile = get_profile(role, profile_id)  # type: ignore[arg-type]
        return str(profile.get("name") or profile_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cliente_profile": self.cliente_profile,
            "sac_profile": self.sac_profile,
            "cliente_profile_name": self._profile_display_name("cliente", self.cliente_profile),
            "sac_profile_name": self._profile_display_name("sac", self.sac_profile),
            "cliente_model": self.cliente_model,
            "sac_model": self.sac_model,
            "cliente_thinking": self.cliente_thinking,
            "sac_thinking": self.sac_thinking,
            "cliente_skills": self.cliente_skills,
            "sac_skills": self.sac_skills,
            "cliente_llm_params": self.cliente_llm_params,
            "sac_llm_params": self.sac_llm_params,
            "status": self.status.value,
            "complaint_title": self.complaint_title,
            "complaint_text": self.complaint_text,
            "response_text": self.response_text,
            "category": self.category,
            "rag_chunks": [
                {
                    "doc_id": c.doc_id,
                    "section": c.section,
                    "text": c.text,
                    "score": c.score,
                }
                for c in self.rag_chunks
            ],
            "turns": [
                {
                    "id": t.id,
                    "role": t.role.value,
                    "text": t.text,
                    "title": t.title,
                    "thinking": t.thinking,
                    "latency_ms": t.latency_ms,
                    "timestamp": t.timestamp,
                }
                for t in self.turns
            ],
        }


THINKING_PATTERN = re.compile(
    r"(?:<think(?:ing)?>|)(.*?)(?:</think(?:ing)?>|)",
    re.DOTALL | re.IGNORECASE,
)


def extract_thinking(text: str) -> tuple[str, str | None]:
    match = THINKING_PATTERN.search(text)
    if not match:
        return text.strip(), None
    thinking = match.group(1).strip()
    clean = THINKING_PATTERN.sub("", text).strip()
    return clean, thinking or None
