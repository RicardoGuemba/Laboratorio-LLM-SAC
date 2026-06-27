from fastapi.testclient import TestClient

from backend.main import app


def test_health():
    with TestClient(app) as client:
        res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "rag" in data
    assert data.get("features", {}).get("manual_complaint") is True


def test_personas_config():
    with TestClient(app) as client:
        res = client.get("/api/personas")
    assert res.status_code == 200
    data = res.json()
    assert "cliente" in data
    assert "sac" in data
    assert "cliente_irritado" in data["cliente"]["profiles"]


def test_knowledge_list():
    with TestClient(app) as client:
        res = client.get("/api/knowledge")
    assert res.status_code == 200
    data = res.json()
    assert len(data["files"]) >= 9


def test_sac_start_session():
    with TestClient(app) as client:
        res = client.post(
            "/api/sac/start",
            json={
                "cliente_profile": "cliente_irritado",
                "sac_profile": "atendente_empatico",
                "cliente_skills": ["mencionar_pedido"],
                "sac_skills": ["politica_reembolso"],
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert data["cliente_profile"] == "cliente_irritado"
