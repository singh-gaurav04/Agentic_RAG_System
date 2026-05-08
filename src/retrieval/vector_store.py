from __future__ import annotations
from typing import Any
from dataclasses import dataclass

from src.config.settings import Settings
from langchain_mistralai import MistralAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone_text.sparse import BM25Encoder 


from pinecone import Pinecone


@dataclass
class EmbeddedChunk:
    id: str
    text: str
    metadata: dict[str, Any]

class VectorStore:
    def __init__(self, settings: Settings) -> None:
        self.settings: Settings = settings
        self._namespace: str = settings.pinecone_namespace
        self._embedder: MistralAIEmbeddings = MistralAIEmbeddings(
            api_key=settings.mistral_api_key,
            model=settings.mistral_embedding_model,
        )
        self.pinecone: Pinecone = Pinecone(
            api_key=settings.pinecone_api_key,
        )
        self.index_name: str = settings.pinecone_index
        self._index = self.pinecone.Index(self.index_name)
        self.vector_store: PineconeVectorStore = PineconeVectorStore(
            embedding=self._embedder,
            index=self._index,
            text_key="text",
            namespace=self._namespace,
        )
        self._bm25_encoder: BM25Encoder = BM25Encoder()
        self._is_bm25_fitted: bool = False

    def add(self,chunks: list[EmbeddedChunk]) -> None:
        if not chunks:
            return
        
        text_chunks : list[str] = [chunk.text for chunk in chunks]
        metadatas :list[dict[str, Any]] = []

        for chunk in chunks:
            metadata: dict[str, Any] = dict(chunk.metadata)
            metadata["id"] = chunk.id
            metadatas.append(metadata)
        
        ids:list[str] = [chunk.id for chunk in chunks]

        self.vector_store.add_texts(
            texts=text_chunks,
            metadatas=metadatas,
            ids=ids
        )
    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        self.add(chunks)


    def count(self) -> int:
            index_stats: dict[str, Any] = self._index.describe_index_stats()
            namespace_stats: dict[str, Any] = index_stats.get("namespaces", {}).get(self._namespace, {})
            return int(namespace_stats.get("vector_count", 0))

        
    def has_paper(self,paper_id:str) -> bool:

            # fetch_response = self.index.fetch(ids=[paper_id], namespace=self.settings.pinecone_namespace)
            # exists = len(fetch_response.vectors) > 0


            response = self.vector_store.similarity_search_with_score(
                query=paper_id,
                k=1,
                filter={"paper_id": paper_id},
            )

            return len(response) > 0

    #=============dense retrieval==================
    def fetch_related_papers(self,query:str,top_k:int) -> dict[str,Any]:
            response = self.vector_store.similarity_search_with_score(
                query=query,
                k=top_k
            )
            ids: list[str] = []
            documents: list[str] = []
            metadatas: list[dict[str, Any]] = []
            distances: list[float] = []

            for document,score in response:
                metadata:dict[str,Any] = dict(document.metadata)
                document_id: str = str(getattr(document, "id", "") or metadata.get("id", ""))

                ids.append(document_id)
                documents.append(document.page_content)
                metadatas.append(metadata)
                distances.append(max(0.0,1.0-score))

            return {
                "ids": [ids],
                "documents": [documents],
                "metadatas": [metadatas],
                "distances": [distances],
            }

    def query_hybrid(self, query: str, top_k: int, alpha: float = 0.5) -> list[dict[str, Any]]:
        if not self._is_bm25_fitted:
            self._fit_bm25_encoder_from_index()
        dense_vector: list[float] = self._embedder.embed_query(query)
        sparse_values: dict[str, list[float] | list[int]] = self._bm25_encoder.encode_queries(query)
        normalized_alpha: float = min(max(alpha, 0.0), 1.0)
        scaled_dense: list[float] = [value * normalized_alpha for value in dense_vector]
        scaled_sparse_values: list[float] = [
            value * (1.0 - normalized_alpha) for value in sparse_values["values"]
        ]
        result: dict[str, Any] = self._index.query(
            vector=scaled_dense,
            sparse_vector={"indices": sparse_values["indices"], "values": scaled_sparse_values},
            top_k=top_k,
            namespace=self._namespace,
            include_metadata=True,
            include_values=False,
        )
        matches: list[dict[str, Any]] = result.get("matches", [])
        items: list[dict[str, Any]] = []
        for match in matches:
            metadata: dict[str, Any] = dict(match.get("metadata", {}))
            items.append(
                {
                    "id": str(match.get("id", "")),
                    "content": str(metadata.get("text", "")),
                    "metadata": metadata,
                    "score": float(match.get("score", 0.0)),
                }
            )
        return items

    def _fit_bm25_encoder_from_index(self) -> None:
        records: dict[str, Any] = self.fetch_all()
        documents: list[str] = records.get("documents", [])
        self._fit_bm25_encoder(documents)

    def _fit_bm25_encoder(self, documents: list[str]) -> None:
        filtered_documents: list[str] = [document for document in documents if document.strip()]
        if not filtered_documents:
            self._is_bm25_fitted = False
            return
        self._bm25_encoder.fit(filtered_documents)
        self._is_bm25_fitted = True

    def fetch_all(self) -> dict[str, Any]:
        ids: list[str] = []
        #return ids in batches
        for batch_ids in self._index.list(namespace=self._namespace):
            ids.extend(batch_ids)
        if not ids:
            return {"ids": [], "documents": [], "metadatas": []}
        fetch_response: dict[str, Any] = self._index.fetch(ids=ids, namespace=self._namespace)
        vectors_by_id: dict[str, dict[str, Any]] = fetch_response.get("vectors", {})
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        ordered_ids: list[str] = []
        for chunk_id in ids:
            vector_data: dict[str, Any] | None = vectors_by_id.get(chunk_id)
            if vector_data is None:
                continue
            metadata: dict[str, Any] = dict(vector_data.get("metadata", {}))
            text: str = str(metadata.pop("text", ""))
            ordered_ids.append(chunk_id)
            documents.append(text)
            metadatas.append(metadata)
        return {"ids": ordered_ids, "documents": documents, "metadatas": metadatas}

    @property
    def embeddings(self) -> MistralAIEmbeddings:
        return self._embedder

    @property
    def bm25_encoder(self) -> BM25Encoder:
        return self._bm25_encoder

    @property
    def index(self):
        return self._index

    @property
    def namespace(self) -> str:
        return self._namespace


