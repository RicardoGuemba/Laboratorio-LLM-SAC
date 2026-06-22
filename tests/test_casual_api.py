from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app, sessions, stream_queues


@pytest.fixture
def client():
    sessions.clear()
    stream_queues.clear()
    return TestClient(app)


def test_start_casual_without_topic(client):
    with patch("backend.main.lm_client.list_models", new=AsyncMock(return_value=["google/gemma-4-12b"])):
        with patch("backend.main.lm_client.pick_model", return_value="google/gemma-4-12b"):
            with patch(
                "backend.main.generate_casual_topic",
                new=AsyncMock(return_value="O preço absurdo do delivery"),
            ):
                res = client.post(
                    "/api/debate/start",
                    json={
                        "mode": "casual",
                        "rico_profile": "herdeiro",
                        "pobre_profile": "doutor",
                        "rico_model": "google/gemma-4-12b",
                        "pobre_model": "google/gemma-4-12b",
                    },
                )
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "casual"
    assert body["topic"] == "O preço absurdo do delivery"
    assert body["topic_starter"] in ("rico", "pobre")
    assert body["rico_position"] == "casual"


def test_start_debate_still_requires_topic(client):
    res = client.post(
        "/api/debate/start",
        json={"mode": "debate", "topic": "ab", "rico_profile": "herdeiro", "pobre_profile": "doutor"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_casual_turn_auto_chains():
    from backend.debate.casual_state_machine import CasualStateMachine
    from backend.debate.session import DebateSession, DebaterId, SessionMode
    from backend.main import _run_casual_turn, _schedule_turn, sessions, stream_queues, running_turns

    session = DebateSession.create(
        topic="Meme viral",
        rico_profile="herdeiro",
        pobre_profile="doutor",
        rico_model="model-a",
        pobre_model="model-b",
        rico_a_favor=True,
        mode=SessionMode.CASUAL,
        topic_starter=DebaterId.RICO,
    )
    sessions[session.id] = session
    stream_queues[session.id] = __import__("asyncio").Queue()
    running_turns.clear()

    machine = CasualStateMachine()
    turn_info = machine.get_turn_info(session)

    with patch(
        "backend.main.lm_client.complete_non_stream",
        new=AsyncMock(return_value=("Cara, viu aquele meme? Não entendi nada.", "")),
    ):
        with patch("backend.main.asyncio.create_task") as task_mock:
            await _run_casual_turn(session.id, turn_info)

    assert len(session.turns) == 1
    assert session.turns[0].text.startswith("Cara, viu")
    task_mock.assert_called_once()


@pytest.mark.asyncio
async def test_kickoff_casual_starts_first_turn():
    from backend.debate.session import DebateSession, DebaterId, SessionMode
    from backend.main import _kickoff_casual, sessions, stream_queues, running_turns

    session = DebateSession.create(
        topic="Café caro",
        rico_profile="herdeiro",
        pobre_profile="doutor",
        rico_model="model-a",
        pobre_model="model-b",
        rico_a_favor=True,
        mode=SessionMode.CASUAL,
        topic_starter=DebaterId.POBRE,
    )
    sessions[session.id] = session
    stream_queues[session.id] = __import__("asyncio").Queue()
    running_turns.clear()

    with patch(
        "backend.main.lm_client.complete_non_stream",
        new=AsyncMock(return_value=("Opa, tudo bem?", "")),
    ):
        await _kickoff_casual(session.id)

    assert len(session.turns) == 1
    assert session.turns[0].debater == DebaterId.POBRE
