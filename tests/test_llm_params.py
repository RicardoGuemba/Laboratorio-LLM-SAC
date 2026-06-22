from backend.debate.llm_params import DEFAULT_LLM_PARAMS, is_chat_model, merge_llm_params


def test_merge_llm_params_defaults():
    merged = merge_llm_params({}, None)
    assert merged["temperature"] == DEFAULT_LLM_PARAMS["temperature"]
    assert merged["top_p"] == DEFAULT_LLM_PARAMS["top_p"]


def test_merge_llm_params_override():
    merged = merge_llm_params({"temperature": 0.5}, {"temperature": 0.9, "max_tokens": 200})
    assert merged["temperature"] == 0.9
    assert merged["max_tokens"] == 200


def test_is_chat_model_filters_embeddings():
    assert is_chat_model("google/gemma-4-12b") is True
    assert is_chat_model("text-embedding-nomic-embed-text-v1.5") is False
