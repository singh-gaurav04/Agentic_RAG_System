from __future__ import annotations
from typing import Any
from dataclasses import dataclass

from src.config.settings import Settings
from langchain_mistralai import MistralAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from pinecone import Pinecone


@dataclass
class EmbeddedChunk:
    id: str
    text: str
    metadata: dict[str, Any]

class VectorStore:
    def __init__(self, settings: Settings) -> None:
        
        self.settings = settings
        self.embeddings = MistralAIEmbeddings(
            api_key=settings.mistral_api_key,
            model=settings.mistral_embedding_model,
        )
        self.pinecone = Pinecone(
            api_key=settings.pinecone_api_key,
        )
        self.index_name = settings.pinecone_index
        
        self.index = self.pinecone.Index(self.index_name)

        vector_store = PineconeVectorStore(
            embedding=self.embeddings,
            index=self.index,
            text_key="text",
        )

        self.sparse_hash_space = 1_000_003

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


        def count(self) -> int:
            index_stats = self.index.describe_index_stats()
            namespace_stats = index_stats.namespace.get("namespaces",{}).get(self.settings.pinecone_namespace,{})
            return namespace_stats.get("vector_count",0)

        
        def has_paper(self,paper_id:str) -> bool:

            # fetch_response = self.index.fetch(ids=[paper_id], namespace=self.settings.pinecone_namespace)
            # exists = len(fetch_response.vectors) > 0


            response = self.vector_store.similarity_search_with_score(
                query=paper_id,
                k=1,
                filter={"paper_id": paper_id}
            )

            return len(response) > 0

        
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

        def fetch_all_papers(self)->dict[str,Any]:
            ids: list[str] = []
        for batch_ids in self.index.list(namespace=self.settings.pinecone_namespace):
            ids.extend(batch_ids)
        if not ids:
            return {"ids": [], "documents": [], "metadatas": []}
        fetch_response: dict[str, Any] = self.index.fetch(ids=ids, namespace=self.settings.pinecone_namespace)
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



