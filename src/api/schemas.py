"""
FastAPI Request and Response Pydantic Schemas for DocLens.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.common.models import Citation, RetrievedChunk


class QueryRequest(BaseModel):
    query: str = Field(..., description="User financial or regulatory query")
    ticker: Optional[str] = Field(None, description="Optional company ticker filter (e.g. MSFT)")
    fiscal_year: Optional[int] = Field(None, description="Optional fiscal year filter (e.g. 2025)")
    use_sparse: bool = Field(True, description="Enable BM25 keyword retrieval")
    use_reranker: bool = Field(True, description="Enable cross-encoder reranking")


class QueryResponse(BaseModel):
    query_log_id: int
    query: str
    answer: str
    is_refusal: bool
    citations: List[Citation]
    retrieved_chunks: List[RetrievedChunk]
    latencies: Dict[str, float]


class FeedbackRequest(BaseModel):
    query_log_id: int
    rating: int = Field(..., ge=-1, le=1, description="1 for Thumbs Up, -1 for Thumbs Down")


class FeedbackResponse(BaseModel):
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    database_connected: bool
    total_indexed_documents: int
    models: Dict[str, str]
