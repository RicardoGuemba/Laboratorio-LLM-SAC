from fastapi.testclient import TestClient

from backend.main import app
from backend.rag.retriever import reindex


def test_sac_simulate_endpoint_starts_background_task():
    with TestClient(app) as client:
        start = client.post(
            "/api/sac/start",
            json={
                "cliente_profile": "cliente_irritado",
                "sac_profile": "atendente_empatico",
            },
        )
        assert start.status_code == 200
        session_id = start.json()["id"]

        simulate = client.post(f"/api/sac/{session_id}/simulate")
        assert simulate.status_code == 200
        assert simulate.json()["started"] is True


def test_sac_respond_endpoint_starts_background_task():
    with TestClient(app) as client:
        start = client.post(
            "/api/sac/start",
            json={
                "cliente_profile": "cliente_irritado",
                "sac_profile": "atendente_empatico",
            },
        )
        assert start.status_code == 200
        session_id = start.json()["id"]

        respond = client.post(
            f"/api/sac/{session_id}/respond",
            json={"complaint": "Meu pedido atrasou e quero reembolso do desodorante."},
        )
        assert respond.status_code == 200
        assert respond.json()["started"] is True
        assert respond.json()["manual"] is True


def test_sac_simulate_rejects_unknown_session():
    with TestClient(app) as client:
        res = client.post("/api/sac/00000000-0000-0000-0000-000000000000/simulate")
        assert res.status_code == 404


def test_health_includes_rag_stats_for_avatar_ui_context():
    reindex()
    with TestClient(app) as client:
        res = client.get("/health")
        data = res.json()
        assert "rag" in data
        assert data["rag"]["chunk_count"] >= 1
