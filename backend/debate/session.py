from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DebaterId(str, Enum):
    RICO = "rico"
    POBRE = "pobre"


class DebatePhase(str, Enum):
    OPENING = "opening"
    ARGUMENT = "argument"
    REPLICA = "replica"
    TREPLICA = "treplica"
    CHAT = "chat"


class SessionMode(str, Enum):
    DEBATE = "debate"
    CASUAL = "casual"


class DebateStatus(str, Enum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ENDED = "ended"


@dataclass
class TurnRecord:
    id: str
    debater: DebaterId
    phase: DebatePhase
    round_num: int
    text: str
    thinking: str | None = None
    reaction_from_peer: dict[str, Any] | None = None
    latency_ms: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Scoreboard:
    buzzwords: int = 0
    yellow_cards: int = 0
    applause: int = 50


@dataclass
class DebateSession:
    id: str
    topic: str
    rico_profile: str
    pobre_profile: str
    rico_model: str
    pobre_model: str
    rico_position: str  # "a_favor" | "contra" | "casual"
    pobre_position: str
    mode: SessionMode = SessionMode.DEBATE
    topic_starter: DebaterId | None = None
    rico_thinking: bool = False
    pobre_thinking: bool = False
    rico_skills: list[str] = field(default_factory=list)
    pobre_skills: list[str] = field(default_factory=list)
    rico_llm_params: dict[str, Any] = field(default_factory=dict)
    pobre_llm_params: dict[str, Any] = field(default_factory=dict)
    status: DebateStatus = DebateStatus.IN_PROGRESS
    current_round: int = 1
    turn_index: int = 0
    last_speaker: DebaterId | None = None
    turns: list[TurnRecord] = field(default_factory=list)
    scoreboard: Scoreboard = field(default_factory=Scoreboard)
    current_stream_text: str = ""
    current_stream_thinking: str = ""

    @staticmethod
    def create(
        topic: str,
        rico_profile: str,
        pobre_profile: str,
        rico_model: str,
        pobre_model: str,
        rico_a_favor: bool,
        rico_thinking: bool = False,
        pobre_thinking: bool = False,
        rico_skills: list[str] | None = None,
        pobre_skills: list[str] | None = None,
        rico_llm_params: dict[str, Any] | None = None,
        pobre_llm_params: dict[str, Any] | None = None,
        mode: SessionMode = SessionMode.DEBATE,
        topic_starter: DebaterId | None = None,
    ) -> DebateSession:
        from backend.debate.persona_store import get_profile, load_defaults

        defaults = load_defaults()
        rico_defaults = defaults.get("rico", {})
        pobre_defaults = defaults.get("pobre", {})

        rico_skill_list = rico_skills or list(
            get_profile("rico", rico_profile).get("default_skills")
            or rico_defaults.get("skills", [])
        )
        pobre_skill_list = pobre_skills or list(
            get_profile("pobre", pobre_profile).get("default_skills")
            or pobre_defaults.get("skills", [])
        )
        if mode == SessionMode.CASUAL:
            positions = ("casual", "casual")
        else:
            positions = (
                "a_favor" if rico_a_favor else "contra",
                "contra" if rico_a_favor else "a_favor",
            )
        return DebateSession(
            id=str(uuid.uuid4()),
            topic=topic,
            rico_profile=rico_profile,
            pobre_profile=pobre_profile,
            rico_model=rico_model,
            pobre_model=pobre_model,
            mode=mode,
            topic_starter=topic_starter,
            rico_position=positions[0],
            pobre_position=positions[1],
            rico_thinking=rico_thinking,
            pobre_thinking=pobre_thinking,
            rico_skills=rico_skill_list,
            pobre_skills=pobre_skill_list,
            rico_llm_params=dict(rico_llm_params or {}),
            pobre_llm_params=dict(pobre_llm_params or {}),
        )

    def get_turns_for(self, debater: DebaterId) -> list[TurnRecord]:
        return [t for t in self.turns if t.debater == debater]

    @staticmethod
    def _profile_display_name(debater: str, profile_id: str) -> str:
        from backend.debate.persona_store import get_profile

        profile = get_profile(debater, profile_id)
        return str(profile.get("name") or profile_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "mode": self.mode.value,
            "topic_starter": self.topic_starter.value if self.topic_starter else None,
            "rico_profile": self.rico_profile,
            "pobre_profile": self.pobre_profile,
            "rico_profile_name": self._profile_display_name("rico", self.rico_profile),
            "pobre_profile_name": self._profile_display_name("pobre", self.pobre_profile),
            "rico_model": self.rico_model,
            "pobre_model": self.pobre_model,
            "rico_position": self.rico_position,
            "pobre_position": self.pobre_position,
            "rico_thinking": self.rico_thinking,
            "pobre_thinking": self.pobre_thinking,
            "rico_skills": self.rico_skills,
            "pobre_skills": self.pobre_skills,
            "rico_llm_params": self.rico_llm_params,
            "pobre_llm_params": self.pobre_llm_params,
            "status": self.status.value,
            "current_round": self.current_round,
            "turn_index": self.turn_index,
            "last_speaker": self.last_speaker.value if self.last_speaker else None,
            "turns": [
                {
                    "id": t.id,
                    "debater": t.debater.value,
                    "phase": t.phase.value,
                    "round_num": t.round_num,
                    "text": t.text,
                    "thinking": t.thinking,
                    "reaction_from_peer": t.reaction_from_peer,
                    "latency_ms": t.latency_ms,
                    "timestamp": t.timestamp,
                }
                for t in self.turns
            ],
            "scoreboard": {
                "buzzwords": self.scoreboard.buzzwords,
                "yellow_cards": self.scoreboard.yellow_cards,
                "applause": self.scoreboard.applause,
            },
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
