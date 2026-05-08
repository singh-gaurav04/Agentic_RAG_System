from __future__ import annotations

from typing import Any

from pinecone import Pinecone

from src.config.settings import Settings

PINECONE_RERANK_MODEL: str = "bge-reranker-v2-m3"


class PineconeRerank:
    def __init__(self, settings: Settings) -> None:
        self.client: Pinecone = Pinecone(api_key=settings.pinecone_api_key)

    def rerank(self, query: str, candidates: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not candidates:
            return []
        candidate_texts: list[str] = [str(candidate.get("content", "")) for candidate in candidates]
        rerank_response = self.client.inference.rerank(
            model=PINECONE_RERANK_MODEL,
            query=query,
            documents=candidate_texts,
            top_n=min(top_k, len(candidate_texts)),
            return_documents=True,
        )
        ranked_items: list[dict[str, Any]] = []
        for match in rerank_response.data:
            candidate_index: int = int(getattr(match, "index", 0))
            candidate: dict[str, Any] = candidates[candidate_index]
            ranked_items.append(
                {
                    "id": candidate["id"],
                    "content": candidate["content"],
                    "metadata": candidate["metadata"],
                    "score": float(getattr(match, "score", 0.0)),
                }
            )
        return ranked_items
