from __future__ import annotations

from typing import Any

BUZZWORDS = [
    "sinergia",
    "disruptivo",
    "mindset",
    "ecossistema",
    "escalável",
    "visionário",
    "elite",
    "meritocracia",
    "game changer",
    "paradigma",
    "stakeholder",
    "deliverable",
    "low hanging fruit",
    "think outside the box",
]

FAKE_AUTHORITY = [
    "estudos mostram",
    "harvard",
    "mckinsey",
    "forbes",
    "87%",
    "92%",
    "cientistas concordam",
    "pesquisas indicam",
    "segundo especialistas",
]

TECHNICAL_MARKERS = [
    "métrica",
    "dado",
    "evidência",
    "experimento",
    "protocolo",
    "amostra",
    "trade-off",
    "sla",
    "otimização",
    "variância",
]


def count_buzzwords(text: str) -> int:
    lower = text.lower()
    return sum(1 for w in BUZZWORDS if w in lower)


def analyze_speaker_gesture(text: str) -> str:
    """Emoção do debatedor que está falando, derivada do conteúdo da fala."""
    lower = text.lower()
    if any(w in lower for w in ("absurdo", "ridículo", "patético", "vergonha", "nonsense")):
        return "deboche"
    if any(w in lower for w in ("evidência", "dado", "métrica", "comprov", "estudo", "análise")):
        return "alegria"
    if any(w in lower for w in ("errado", "falso", "mentira", "inaceitável", "nunca", "jamais")):
        return "rejeicao"
    if count_buzzwords(text) >= 2:
        return "deboche"
    return "talk"


def analyze_reaction(text: str, listener: str) -> dict[str, Any]:
    lower = text.lower()
    buzzword_count = count_buzzwords(text)
    has_fake_citation = any(m in lower for m in FAKE_AUTHORITY)
    has_technical = any(m in lower for m in TECHNICAL_MARKERS)
    word_count = len(text.split())
    is_long = word_count > 120

    score = 0
    gesture = "shrug"
    reaction = "neutral"
    one_liner = "..."

    if buzzword_count >= 3:
        score -= 40
        gesture = "deboche"
        reaction = "mockery"
        one_liner = "Quantos buzzwords cabem numa frase?"
    elif has_fake_citation:
        score -= 30
        gesture = "deboche"
        reaction = "mockery"
        one_liner = "Fonte: trust me bro?"
    elif listener == "rico" and has_technical:
        score -= 10
        gesture = "rejeicao"
        reaction = "reject"
        one_liner = "Isso é técnico demais pro meu ecossistema."
    elif has_technical:
        score += 25
        gesture = "alegria"
        reaction = "joy"
        one_liner = "Finalmente, substância."
    elif is_long:
        score -= 15
        gesture = "rejeicao"
        reaction = "reject"
        one_liner = "Podia resumir?"
    else:
        score += 5
        gesture = "shrug"
        reaction = "neutral"
        one_liner = "Hmm."

    return {
        "score": score,
        "gesture": gesture,
        "reaction": reaction,
        "one_liner": one_liner,
        "buzzword_count": buzzword_count,
        "yellow_card": has_fake_citation and listener == "pobre",
    }


def update_scoreboard(session_scoreboard: Any, text: str, reaction: dict[str, Any]) -> None:
    session_scoreboard.buzzwords += reaction.get("buzzword_count", 0)
    if reaction.get("yellow_card"):
        session_scoreboard.yellow_cards += 1
    session_scoreboard.applause = max(
        0, min(100, session_scoreboard.applause + reaction.get("score", 0) // 5)
    )
