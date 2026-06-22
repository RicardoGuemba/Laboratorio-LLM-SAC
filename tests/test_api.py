from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    with patch("backend.main.lm_client.health_check", new=AsyncMock(return_value={"online": True, "models": ["google/gemma-4-12b"]})):
        res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_personas_config(client):
    res = client.get("/api/personas")
    assert res.status_code == 200
    data = res.json()
    assert "rico" in data
    assert "pobre" in data
    assert "herdeiro" in data["rico"]["profiles"]


def test_start_debate_validation(client):
    res = client.post(
        "/api/debate/start",
        json={"mode": "debate", "topic": "ab", "rico_profile": "herdeiro", "pobre_profile": "doutor"},
    )
    assert res.status_code == 400


def test_start_debate_success(client):
    with patch("backend.main.lm_client.list_models", new=AsyncMock(return_value=["google/gemma-4-12b", "lfm2.5-1.2b-thinking-mlx"])):
        with patch("backend.main.lm_client.pick_model", side_effect=lambda override, debater, available: override or available[0]):
                res = client.post(
                    "/api/debate/start",
                    json={
                        "mode": "debate",
                        "topic": "Deve existir imposto sobre herança?",
                    "rico_profile": "herdeiro",
                    "pobre_profile": "doutor",
                    "rico_model": "google/gemma-4-12b",
                    "pobre_model": "lfm2.5-1.2b-thinking-mlx",
                    "rico_llm_params": {"temperature": 0.6, "top_p": 0.85, "max_tokens": 180},
                },
            )
    assert res.status_code == 200
    body = res.json()
    assert body["topic"].startswith("Deve existir")
    assert body["rico_llm_params"]["temperature"] == 0.6
    assert body["rico_profile_name"] == "Rico Montecristo III"
    assert body["pobre_profile_name"]
