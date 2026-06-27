import asyncio
from unittest.mock import MagicMock

from backend.sac.orchestrator import run_manual_response, run_simulation
from backend.sac.session import SacSession, SacStatus


def test_run_simulation_emits_full_cycle():
    session = SacSession.create(
        cliente_profile="cliente_irritado",
        sac_profile="atendente_empatico",
        cliente_model="test-cliente",
        sac_model="test-sac",
        cliente_skills=["mencionar_pedido"],
        sac_skills=["politica_reembolso"],
    )

    events: list[dict] = []

    async def emit(event: dict | None) -> None:
        if event is not None:
            events.append(event)

    lm_client = MagicMock()
    complaint_text = "TITULO: Atraso absurdo\nCORPO:\nComprei e não chegou. Isso é inaceitável!"
    response_text = "Olá! Pedimos sinceras desculpas e vamos resolver seu pedido."

    async def fake_generate(*args, **kwargs):
        if kwargs.get("stream_role") == "cliente":
            return complaint_text
        return response_text

    import backend.sac.orchestrator as orchestrator

    original = orchestrator._generate_text
    orchestrator._generate_text = fake_generate
    try:
        result = asyncio.run(run_simulation(session, lm_client, emit))
    finally:
        orchestrator._generate_text = original

    assert result.status == SacStatus.COMPLETED
    assert result.complaint_title == "Atraso absurdo"
    assert "inaceitável" in result.complaint_text
    assert "desculpas" in result.response_text
    assert len(result.turns) == 2

    event_types = [e["type"] for e in events]
    assert event_types[0] == "complaint_start"
    assert "complaint_done" in event_types
    assert "rag_context" in event_types
    assert "response_start" in event_types
    assert event_types[-1] == "response_done"
    assert events[0]["role"] == "cliente"
    response_start_idx = event_types.index("response_start")
    assert events[response_start_idx]["role"] == "sac"
    rag_idx = event_types.index("rag_context")
    assert isinstance(events[rag_idx]["chunks"], list)


def test_run_simulation_includes_rag_chunks():
    session = SacSession.create(
        cliente_profile="cliente_irritado",
        sac_profile="atendente_empatico",
        cliente_model="m1",
        sac_model="m2",
    )
    rag_events: list[dict] = []

    async def emit(event: dict | None) -> None:
        if event and event.get("type") == "rag_context":
            rag_events.append(event)

    import backend.sac.orchestrator as orchestrator

    async def fake_generate(*args, **kwargs):
        return (
            "TITULO: Produto vencido\nCORPO:\nRecebi Tallow Balm vencido, quero reembolso."
            if kwargs.get("stream_role") == "cliente"
            else "Lamentamos e processaremos reembolso integral."
        )

    original = orchestrator._generate_text
    orchestrator._generate_text = fake_generate
    try:
        asyncio.run(run_simulation(session, MagicMock(), emit))
    finally:
        orchestrator._generate_text = original

    assert len(rag_events) == 1
    chunks = rag_events[0]["chunks"]
    assert len(chunks) >= 1
    assert any("vencido" in c["text"].lower() or "reembolso" in c["text"].lower() for c in chunks)


def test_run_manual_response_uses_user_complaint_and_sac_llm():
    session = SacSession.create(
        cliente_profile="cliente_irritado",
        sac_profile="atendente_empatico",
        cliente_model="m1",
        sac_model="m2",
    )
    events: list[dict] = []

    async def emit(event: dict | None) -> None:
        if event is not None:
            events.append(event)

    import backend.sac.orchestrator as orchestrator

    async def fake_generate(*args, **kwargs):
        assert kwargs.get("stream_role") == "sac"
        return "Olá! Pedimos sinceras desculpas e vamos rastrear seu pedido."

    original = orchestrator._generate_text
    orchestrator._generate_text = fake_generate
    try:
        result = asyncio.run(
            run_manual_response(
                session,
                "Meu pedido #TP-123 atrasou e ninguém responde.",
                MagicMock(),
                emit,
            )
        )
    finally:
        orchestrator._generate_text = original

    assert result.status == SacStatus.COMPLETED
    assert "pedido" in result.complaint_text.lower()
    assert "desculpas" in result.response_text
    types = [e["type"] for e in events]
    assert events[0].get("manual") is True
    assert "complaint_done" in types
    assert "response_done" in types
