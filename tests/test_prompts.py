from backend.debate.prompts import build_messages
from backend.debate.session import DebatePhase, DebateSession, DebaterId


def test_build_messages_includes_profile_prompt():
    session = DebateSession.create(
        topic="Deve existir imposto sobre herança?",
        rico_profile="herdeiro",
        pobre_profile="doutor",
        rico_model="google/gemma-4-12b",
        pobre_model="lfm2.5-1.2b-thinking-mlx",
        rico_a_favor=False,
        rico_skills=["jargao_premium"],
        pobre_skills=["reducao_dimensional"],
    )
    messages = build_messages(
        session,
        DebaterId.RICO,
        DebatePhase.OPENING,
        None,
        thinking=False,
    )
    system = messages[0]["content"]
    assert "PERFIL DE PERSONALIDADE" in system
    assert "SKILLS ADICIONAIS" in system
