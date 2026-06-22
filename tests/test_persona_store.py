from backend.debate.persona_store import (
    parse_profile_md,
    render_profile_md,
    validate_debate_selection,
)


def test_parse_profile_with_prompt():
    content = """# teste
nome: Teste
---
Resumo curto
Comporte-se de forma irônica e técnica.
"""
    parsed = parse_profile_md(content)
    assert parsed["id"] == "teste"
    assert parsed["description"] == "Resumo curto"
    assert "irônica" in parsed["prompt"]


def test_render_profile_roundtrip():
    data = {
        "id": "herdeiro",
        "name": "Herdeiro",
        "description": "Esnobe e arrogante.",
        "prompt": "Fale como herdeiro esnobe usando jargão premium.",
        "default_skills": ["jargao_premium"],
    }
    rendered = render_profile_md(data)
    parsed = parse_profile_md(rendered)
    assert parsed["prompt"] == data["prompt"]


def test_validate_allows_profile_without_skills():
    validate_debate_selection("rico", "herdeiro", [])
