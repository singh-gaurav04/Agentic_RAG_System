from __future__ import annotations

from typing import Any

from langchain_community.retrievers import PineconeHybridSearchRetriever

from src.config.settings import Settings
from src.schemas.agent_schema import DocumentMetadata, RetrievedDocument
from src.retrieval.reranker import PineconeRerank
from src.retrieval.vector_store import VectorStore


class HybridRetriever:
    def __init__(self, settings: Settings, vector_repository: VectorStore) -> None:
        self._settings: Settings = settings
        self._vector_store: VectorStore = vector_store
        self._reranker: PineconeRerank = PineconeRerank(settings)

    def rebuild_sparse_index(self) -> None:
        # Pinecone hybrid search builds sparse signal at query-time; no local index needed.
        return

    def retrieve(self, query: str) -> list[RetrievedDocument]:
        raw_documents = self._hybrid_retriever.invoke(query)
        hybrid_candidates: list[dict[str, Any]] = []
        for document in raw_documents:
            metadata: dict[str, Any] = dict(document.metadata)
            hybrid_candidates.append(
                {
                    "id": str(metadata.get("chunk_id", "")),
                    "content": document.page_content,
                    "metadata": metadata,
                    "score": 0.0,
                }
            )
        reranked_candidates = self._reranker.rerank(
            query=query,
            candidates=hybrid_candidates,
            top_k=self._settings.top_k_final,
        )
        retrieved_documents: list[RetrievedDocument] = []
        for candidate in reranked_candidates:
            rerank_score: float = float(candidate.get("score", 0.0))
            metadata: DocumentMetadata = DocumentMetadata.model_validate(candidate.get("metadata", {}))
            retrieved_documents.append(
                RetrievedDocument(
                    id=str(candidate.get("id", "")),
                    content=str(candidate.get("content", "")),
                    metadata=metadata,
                    dense_score=rerank_score,
                    rerank_score=rerank_score,
                    final_score=rerank_score,
                )
            )
        return [
            document
            for document in retrieved_documents
            if document.final_score >= self._settings.min_retrieval_score
        ]
