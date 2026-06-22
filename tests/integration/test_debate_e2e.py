#!/usr/bin/env python3
"""Validação end-to-end de debate formal (requer servidor + LM Studio)."""
from __future__ import annotations

import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8765"
TOPIC = "Qual característica de uma presidente é a mais relevante?"


def wait_turn(client: httpx.Client, session_id: str, timeout: float) -> dict:
    turn_done: dict | None = None
    start = time.monotonic()
    with client.stream("GET", f"/api/debate/{session_id}/stream", timeout=timeout) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if time.monotonic() - start > timeout:
                break
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if event.get("type") == "turn_done":
                turn_done = event
                break
    if not turn_done:
        raise RuntimeError("turn_done não recebido")
    return turn_done


def main() -> int:
    print("=== Teste debate formal (E2E) ===")
    print(f"Tema: {TOPIC}\n")

    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        health = client.get("/health").json()
        if not health.get("lmstudio", {}).get("online"):
            print("ERRO: LM Studio offline")
            return 1
        print("LM Studio: online")

        session = client.post(
            "/api/debate/start",
            json={
                "mode": "debate",
                "topic": TOPIC,
                "rico_profile": "herdeiro",
                "pobre_profile": "doutor",
                "rico_thinking": False,
                "pobre_thinking": False,
            },
        ).json()
        sid = session["id"]
        print(f"Sessão: {sid}")
        print(f"Rico: {session['rico_position']} | Pobre: {session['pobre_position']}\n")

        timeouts = {"rico": 320.0, "pobre": 150.0}
        for i, label in enumerate(["Rico (Abertura)", "Pobre (Abertura)"], 1):
            print(f"--- Turno {i}: {label} ---")
            client.post(f"/api/debate/{sid}/next")
            debater_key = "rico" if i == 1 else "pobre"
            result = wait_turn(client, sid, timeouts[debater_key])
            text = result["turn"]["text"].strip()
            debater = result["turn"]["debater"]
            print(f"Debatedor: {debater}")
            print(f"Texto ({len(text)} chars): {text[:280]}{'...' if len(text) > 280 else ''}")
            if len(text) < 50:
                print("FALHA: texto muito curto — esperado debate substantivo")
                return 1
            print(f"Placar: {result['scoreboard']}\n")

        state = client.get(f"/api/debate/{sid}").json()
        print("=== SUCESSO: 2/2 turnos com fala válida ===")
        print(f"Total turnos registrados: {len(state['turns'])}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.ConnectError:
        print(f"ERRO: servidor não acessível em {BASE}")
        print("Inicie com: PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8765")
        sys.exit(1)
