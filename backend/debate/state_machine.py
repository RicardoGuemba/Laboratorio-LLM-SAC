from __future__ import annotations

from dataclasses import dataclass

from backend.debate.session import DebatePhase, DebateSession, DebaterId


PHASE_ORDER = [
    DebatePhase.OPENING,
    DebatePhase.ARGUMENT,
    DebatePhase.REPLICA,
    DebatePhase.TREPLICA,
]


@dataclass
class TurnInfo:
    debater: DebaterId
    phase: DebatePhase
    round_num: int
    is_complete: bool = False


class DebateStateMachine:
    def __init__(self, max_rounds: int = 3) -> None:
        self.max_rounds = max_rounds
        self._total_turns = max_rounds * len(PHASE_ORDER)

    def get_turn_info(self, session: DebateSession) -> TurnInfo | None:
        if session.turn_index >= self._total_turns:
            return None
        round_num = session.turn_index // len(PHASE_ORDER) + 1
        phase = PHASE_ORDER[session.turn_index % len(PHASE_ORDER)]
        debater = self._speaker_for_turn(session, phase)
        return TurnInfo(debater=debater, phase=phase, round_num=round_num)

    def _speaker_for_turn(self, session: DebateSession, phase: DebatePhase) -> DebaterId:
        if phase == DebatePhase.OPENING:
            return DebaterId.RICO
        if phase == DebatePhase.ARGUMENT:
            return DebaterId.POBRE if session.last_speaker == DebaterId.RICO else DebaterId.RICO
        if phase == DebatePhase.REPLICA:
            if session.last_speaker is None:
                return DebaterId.POBRE
            return DebaterId.POBRE if session.last_speaker == DebaterId.RICO else DebaterId.RICO
        # treplica: o outro debatedor responde à réplica (alternância)
        if session.last_speaker is None:
            return DebaterId.RICO
        return DebaterId.POBRE if session.last_speaker == DebaterId.RICO else DebaterId.RICO

    def advance(self, session: DebateSession) -> None:
        session.turn_index += 1
        new_round = session.turn_index // len(PHASE_ORDER) + 1
        session.current_round = min(new_round, self.max_rounds)
        if session.turn_index >= self._total_turns:
            from backend.debate.session import DebateStatus

            session.status = DebateStatus.COMPLETED

    def is_finished(self, session: DebateSession) -> bool:
        return session.turn_index >= self._total_turns or session.status.value in (
            "completed",
            "ended",
        )
