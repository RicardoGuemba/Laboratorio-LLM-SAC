from backend.reactions.heuristics import analyze_speaker_gesture


def test_speaker_gesture_deboche():
    assert analyze_speaker_gesture("Isso é absolutamente ridículo e patético.") == "deboche"


def test_speaker_gesture_alegria():
    assert analyze_speaker_gesture("Os dados e a evidência comprovam minha tese.") == "alegria"


def test_speaker_gesture_default_talk():
    assert analyze_speaker_gesture("Concordo parcialmente com o ponto levantado.") == "talk"
