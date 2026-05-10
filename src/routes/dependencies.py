from __future__ import annotations

from functools import lru_cache

from src.config.settings import Settings, get_settings
from src.retrieval.vector_store import VectorStore

from src.tools.web_search_tool import WebSearchTool
from src.graph.nodes import GraphNodes
from src.graph.workflow import build_graph
from src.ingestion.arxiv_ingestor import ArxivIngestor
from src.memory.memory_store import MemoryStore
from src.retrieval.hybrid_retriever import HybridRetriever
from langgraph.checkpoint.memory import InMemorySaver


@lru_cache
def get_vector_store() -> VectorStore:
    settings: Settings = get_settings()
    return VectorStore(settings)


@lru_cache
def get_memory_store() -> MemoryStore:
    settings: Settings = get_settings()
    return MemoryStore(settings)


@lru_cache
def get_retriever() -> HybridRetriever:
    settings: Settings = get_settings()
    retriever: HybridRetriever = HybridRetriever(settings, get_vector_store())
    # Build sparse index once on startup; rebuilt after ingestion updates.
    retriever.rebuild_sparse_index()
    return retriever


@lru_cache
def get_ingestor() -> ArxivIngestor:
    settings: Settings = get_settings()
    return ArxivIngestor(settings, get_vector_store())


@lru_cache
def get_graph():
    checkpointer = InMemorySaver()
    settings: Settings = get_settings()
    nodes: GraphNodes = GraphNodes(
        settings=settings,
        retriever=get_retriever(),
        # memory_store=get_memory_store(),
        web_search_tool=WebSearchTool(),
    )
    return build_graph(nodes, checkpointer=checkpointer)
