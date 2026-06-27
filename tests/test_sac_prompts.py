from backend.sac.prompts import (
    enforce_max_sentences,
    infer_complaint_category,
    parse_complaint_output,
    parse_manual_complaint,
    pick_complaint_category,
)
from backend.sac.session import SacSession


def test_parse_complaint_output():
    raw = """TITULO: Atraso na entrega
CORPO:
Comprei há duas semanas e nada chegou. Estou indignado."""
    title, body = parse_complaint_output(raw)
    assert title == "Atraso na entrega"
    assert "duas semanas" in body


def test_enforce_max_sentences():
    text = "Uma. Duas. Três. Quatro. Cinco."
    result = enforce_max_sentences(text, 3)
    assert result.count(".") == 3


def test_pick_category():
    cat = pick_complaint_category()
    assert isinstance(cat, str)
    assert len(cat) > 0


def test_sac_session_create():
    session = SacSession.create(
        cliente_profile="cliente_irritado",
        sac_profile="atendente_empatico",
        cliente_model="test-model",
        sac_model="test-model-2",
    )
    assert session.cliente_profile == "cliente_irritado"
    assert session.sac_profile == "atendente_empatico"
    assert len(session.cliente_skills) >= 1


def test_parse_manual_complaint_multiline_title():
    title, body = parse_manual_complaint("Atraso na entrega\nComprei há duas semanas e nada chegou.")
    assert title == "Atraso na entrega"
    assert "duas semanas" in body


def test_infer_complaint_category_from_text():
    cat = infer_complaint_category("Quero reembolso do desodorante que não funcionou")
    assert cat in {"reembolso", "desodorante_ineficaz"}
