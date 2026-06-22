from __future__ import annotations

from dataclasses import dataclass

from backend.debate.session import DebatePhase, DebateSession, DebaterId


@dataclass
class TurnInfo:
    debater: DebaterId
    phase: DebatePhase
    round_num: int
    is_complete: bool = False


class CasualStateMachine:
    """Conversa casual infinita até status ENDED."""

    def get_turn_info(self, session: DebateSession) -> TurnInfo | None:
        if self.is_finished(session):
            return None
        debater = self._speaker_for_turn(session)
        round_num = session.turn_index + 1
        return TurnInfo(debater=debater, phase=DebatePhase.CHAT, round_num=round_num)

    def _speaker_for_turn(self, session: DebateSession) -> DebaterId:
        if session.turn_index == 0:
            return session.topic_starter or DebaterId.RICO
        if session.last_speaker is None:
            return session.topic_starter or DebaterId.RICO
        return (
            DebaterId.POBRE
            if session.last_speaker == DebaterId.RICO
            else DebaterId.RICO
        )

    def advance(self, session: DebateSession) -> None:
        session.turn_index += 1
        session.current_round = session.turn_index

    def is_finished(self, session: DebateSession) -> bool:
        return session.status.value in ("completed", "ended")
