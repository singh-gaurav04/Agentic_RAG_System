from __future__ import annotations

from typing import Any

from src.config.settings import Settings
from src.schemas.agent_schema import DocumentMetadata, RetrievedDocument
from src.retrieval.reranker import PineconeRerank
from src.retrieval.vector_store import VectorStore


class HybridRetriever:
    def __init__(self, settings: Settings, vector_repository: VectorStore) -> None:
        self.settings: Settings = settings
        self.vector_store: VectorStore = vector_repository
        self.reranker: PineconeRerank = PineconeRerank(settings)

    def rebuild_sparse_index(self) -> None:
        # Pinecone hybrid search builds sparse signal at query-time; no local index needed.
        return

    async def retrieve(self, query: str) -> list[RetrievedDocument]:
        hybrid_candidates: list[dict[str, Any]] = self.vector_store.query_hybrid(
            query=query,
            top_k=self.settings.top_k_final,
        )
        if not hybrid_candidates:
            return []
        reranked_candidates = self.reranker.rerank(
            query=query,
            candidates=hybrid_candidates,
            top_k=self.settings.top_k_final,
        )
        candidate_by_id: dict[str, dict[str, Any]] = {
            str(candidate.get("id", "")): candidate for candidate in hybrid_candidates
        }
        if not reranked_candidates:
            reranked_candidates = hybrid_candidates
        retrieved_documents: list[RetrievedDocument] = []
        for candidate in reranked_candidates:
            candidate_id: str = str(candidate.get("id", ""))
            source_candidate: dict[str, Any] = candidate_by_id.get(candidate_id, candidate)
            dense_score: float = float(source_candidate.get("score", 0.0))
            rerank_score: float = float(candidate.get("score", 0.0))
            metadata_payload: dict[str, Any] = source_candidate.get("metadata", {})
            metadata: DocumentMetadata = DocumentMetadata.model_validate(metadata_payload)
            final_score: float = max(dense_score, rerank_score)
            retrieved_documents.append(
                RetrievedDocument(
                    id=candidate_id,
                    content=str(source_candidate.get("content", "")),
                    metadata=metadata,
                    dense_score=dense_score,
                    rerank_score=rerank_score,
                    final_score=final_score,
                )
            )
        return retrieved_documents
