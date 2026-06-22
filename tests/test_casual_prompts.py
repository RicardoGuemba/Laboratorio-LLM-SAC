from backend.debate.casual_prompts import (
    build_casual_messages,
    build_casual_system_prompt,
    enforce_max_sentences,
)
from backend.debate.session import DebateSession, DebaterId, SessionMode


def _session() -> DebateSession:
    return DebateSession.create(
        topic="Fila do mercado no sábado",
        rico_profile="herdeiro",
        pobre_profile="doutor",
        rico_model="model-a",
        pobre_model="model-b",
        rico_a_favor=True,
        mode=SessionMode.CASUAL,
        topic_starter=DebaterId.RICO,
    )


def test_casual_system_prompt_uses_persona_not_debate_position():
    session = _session()
    prompt = build_casual_system_prompt(session, DebaterId.RICO)
    assert "Fila do mercado" in prompt
    assert "Estou A FAVOR" not in prompt
    assert "Estou CONTRA" not in prompt
    assert "no máximo 5 frases" in prompt.lower() or "5 frases" in prompt


def test_casual_messages_include_opener_instruction():
    session = _session()
    messages = build_casual_messages(session, DebaterId.RICO)
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert "Inicie a conversa" in messages[-1]["content"]


def test_enforce_max_sentences():
    text = "Um. Dois. Três. Quatro. Cinco. Seis. Sete."
    result = enforce_max_sentences(text, maximum=5)
    assert result.count(".") == 5


def test_enforce_max_sentences_keeps_short_text():
    text = "Só uma frase curta."
    assert enforce_max_sentences(text, maximum=5) == text
