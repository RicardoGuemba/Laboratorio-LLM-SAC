from backend.debate.casual_state_machine import CasualStateMachine
from backend.debate.session import DebatePhase, DebateSession, DebateStatus, DebaterId, SessionMode


def _session(**kwargs) -> DebateSession:
    base = DebateSession.create(
        topic="Café caro demais",
        rico_profile="herdeiro",
        pobre_profile="doutor",
        rico_model="model-a",
        pobre_model="model-b",
        rico_a_favor=True,
        mode=SessionMode.CASUAL,
        topic_starter=DebaterId.POBRE,
    )
    for key, value in kwargs.items():
        setattr(base, key, value)
    return base


def test_first_speaker_is_topic_starter():
    machine = CasualStateMachine()
    session = _session(topic_starter=DebaterId.POBRE)
    info = machine.get_turn_info(session)
    assert info is not None
    assert info.debater == DebaterId.POBRE
    assert info.phase == DebatePhase.CHAT


def test_alternates_speakers():
    machine = CasualStateMachine()
    session = _session(topic_starter=DebaterId.RICO)
    session.last_speaker = DebaterId.RICO
    session.turn_index = 1
    info = machine.get_turn_info(session)
    assert info is not None
    assert info.debater == DebaterId.POBRE


def test_never_finishes_until_ended():
    machine = CasualStateMachine()
    session = _session()
    session.turn_index = 100
    assert not machine.is_finished(session)
    session.status = DebateStatus.ENDED
    assert machine.is_finished(session)
    assert machine.get_turn_info(session) is None


def test_advance_increments_turn_index():
    machine = CasualStateMachine()
    session = _session()
    machine.advance(session)
    assert session.turn_index == 1
    assert session.current_round == 1
