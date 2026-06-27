from backend.personas.persona_store import get_personas_config, validate_role_selection


def test_personas_config_has_cliente_sac():
    cfg = get_personas_config()
    assert "cliente" in cfg
    assert "sac" in cfg
    assert "cliente_irritado" in cfg["cliente"]["profiles"]
    assert "atendente_empatico" in cfg["sac"]["profiles"]


def test_validate_role_selection_ok():
    validate_role_selection("cliente", "cliente_irritado", ["mencionar_pedido"])


def test_validate_role_selection_bad_profile():
    import pytest

    with pytest.raises(ValueError, match="não existe"):
        validate_role_selection("cliente", "inexistente", [])
