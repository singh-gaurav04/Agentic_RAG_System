from pydantic import BaseModel, Field
from enum import Enum
from typing import Any
from datetime import datetime
from typing import Literal


#============= Agent Action Enum =============
class AgentAction(Enum):
    retrieve_documents = "retrieve_documents"
    ask_clarification = "ask_clarification"
    web_search = "web_search"
    answer = "answer"
    refuse = "refuse"
    rewrite_query = "rewrite_query"
    rerank_results = "rerank_results"

#==================Chat Schema =============
class ChatRequest(BaseModel):
    session_id: str
    user_query: str
    history: list[dict[str, Any]] = Field(default_factory=list)

class ChatResponse(BaseModel):
    session_id: str
    answer: str
    action: AgentAction
    confidence: float
    references: list[Reference] = Field(default_factory=list)
    traces: list[dict[str, Any]] = Field(default_factory=list) # for agent tracing purpose


#=============Reference Schema =============
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Reference(BaseModel):
    paper_id: str
    title: str
    source_url: str
    section: str

#=============planner Decisions schema =============
class PlannerDecision(BaseModel):
    action: AgentAction
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    rewritten_query: str | None = None
    clarification_question: str | None = None
    refusal_reason: str | None = None

#==================Ingest Schema =============
class IngestRequest(BaseModel):
    max_papers: int = Field(default=50, ge=1, le=200, description="Maximum number of papers to ingest")
    category: str = Field(default="cs.AI", description="Category of papers to ingest")
    days_back: int = Field(default=90, ge=1, le=365, description="Number of days back to ingest papers")
    batch_size: int = Field(default=10, ge=1, le=50, description="Number of papers to ingest in each batch")

class IngestResponse(BaseModel):
    requested: int
    indexed: int
    skipped_duplicates: int
    failed: int
    failures: list[str]


#=============Document Schema =============
class DocumentMetadata(BaseModel):
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    section: str
    source_url: str
    published_at: datetime
    chunk_index: int


class RetrievedDocument(BaseModel):
    id: str
    content: str
    metadata: DocumentMetadata
    dense_score: float = 0.0
    bm25_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0
