from backend.debate.topic_generator import _clean_topic, _is_valid_topic


def test_rejects_english_meta_topic():
    raw = "Okay, let's tackle this. The user wants me to respond as Prof. Pobre"
    cleaned = _clean_topic(raw)
    assert not _is_valid_topic(cleaned)


def test_accepts_portuguese_topic():
    assert _is_valid_topic("O preço absurdo do delivery ontem à noite")


def test_rejects_too_short():
    assert not _is_valid_topic("Café")
