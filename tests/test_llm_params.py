from backend.llm.llm_params import is_chat_model, merge_llm_params


def test_is_chat_model():
    assert is_chat_model("google/gemma-4-12b")
    assert not is_chat_model("text-embedding-nomic-embed-text-v1.5")


def test_merge_llm_params():
    base = {"temperature": 0.5, "top_p": 0.8, "max_tokens_direct": 200}
    merged = merge_llm_params(base, {"temperature": 0.9})
    assert merged["temperature"] == 0.9
    assert merged["max_tokens"] == 200
