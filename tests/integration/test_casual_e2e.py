#!/usr/bin/env python3
"""Validação end-to-end da conversa casual (requer servidor + LM Studio)."""
from __future__ import annotations

import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8765"


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
    print("=== Teste conversa casual (E2E) ===")
    with httpx.Client(base_url=BASE, timeout=120.0) as client:
        start = client.post(
            "/api/debate/start",
            json={
                "mode": "casual",
                "rico_profile": "herdeiro",
                "pobre_profile": "doutor",
            },
        )
        if start.status_code != 200:
            print(f"ERRO start: {start.status_code} {start.text}")
            return 1
        session = start.json()
        if session.get("mode") != "casual":
            print("ERRO: servidor sem suporte a mode=casual — reinicie o backend")
            return 1
        sid = session["id"]
        print(f"Sessão: {sid}")
        print(f"Tema: {session.get('topic', '')}")
        print(f"Iniciador: {session.get('topic_starter')}")

        result = wait_turn(client, sid, timeout=120.0)
        text = result["turn"]["text"].strip()
        print(f"1ª fala ({result['turn']['debater']}): {text[:200]}")
        if len(text) < 5:
            print("FALHA: primeira fala vazia ou muito curta")
            return 1

        state = client.get(f"/api/debate/{sid}").json()
        print(f"Turnos registrados: {len(state['turns'])}")
        print("=== SUCESSO: conversa casual iniciou ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.ConnectError:
        print(f"ERRO: servidor não acessível em {BASE}")
        sys.exit(1)
