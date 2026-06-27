from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from rank_bm25 import BM25Okapi

from backend.rag.loader import Chunk, document_to_chunks, load_all_documents


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-záàâãéêíóôõúç0-9]+", text.lower())


class BM25Index:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self._bm25: BM25Okapi | None = None
        self.last_indexed: str | None = None
        self.doc_count: int = 0

    def rebuild(self) -> dict[str, Any]:
        docs = load_all_documents()
        self.doc_count = len(docs)
        self.chunks = []
        for doc in docs:
            self.chunks.extend(document_to_chunks(doc))

        if self.chunks:
            corpus = [_tokenize(c.text) for c in self.chunks]
            self._bm25 = BM25Okapi(corpus)
        else:
            self._bm25 = None

        self.last_indexed = datetime.now(timezone.utc).isoformat()
        return self.stats()

    def stats(self) -> dict[str, Any]:
        return {
            "doc_count": self.doc_count,
            "chunk_count": len(self.chunks),
            "last_indexed": self.last_indexed,
        }

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.1,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._bm25 or not self.chunks:
            return []

        enriched_query = query
        if category:
            enriched_query = f"{category} {query}"

        scores = self._bm25.get_scores(_tokenize(enriched_query))
        ranked = sorted(
            zip(self.chunks, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        results: list[dict[str, Any]] = []
        for chunk, score in ranked[: top_k * 2]:
            if score < min_score:
                continue
            results.append(
                {
                    "doc_id": chunk.doc_id,
                    "section": chunk.section,
                    "text": chunk.text,
                    "score": float(score),
                    "metadata": chunk.metadata,
                }
            )
            if len(results) >= top_k:
                break
        return results


# Singleton index
_index = BM25Index()


def get_index() -> BM25Index:
    return _index


def reindex() -> dict[str, Any]:
    return _index.rebuild()
