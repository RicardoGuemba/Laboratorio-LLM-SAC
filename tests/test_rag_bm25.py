from backend.rag.loader import load_all_documents, validate_knowledge_content
from backend.rag.retriever import BM25Index


def test_load_documents():
    docs = load_all_documents()
    assert len(docs) >= 9
    assert all(d.complaint or d.response or d.raw_content for d in docs)


def test_bm25_retrieve_atraso_entrega():
    index = BM25Index()
    stats = index.rebuild()
    assert stats["chunk_count"] > 0

    results = index.retrieve("atraso entrega pedido não chegou rastreio", top_k=3)
    assert len(results) >= 1
    assert any("atraso" in r["text"].lower() or "entrega" in r["text"].lower() for r in results)


def test_validate_knowledge_schema():
    valid = """---
id: test-01
categoria: atraso_entrega
---
# Test

## Reclamação do cliente
Texto da reclamação aqui.

## Resposta TRUEPALEO SAC
Texto da resposta aqui.
"""
    assert validate_knowledge_content(valid) == []

    invalid = """---
id: test-02
---
# Sem seções
"""
    errors = validate_knowledge_content(invalid)
    assert any("categoria" in e for e in errors)
