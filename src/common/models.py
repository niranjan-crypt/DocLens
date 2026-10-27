"""
Domain data models and schemas for DocLens.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Lineage metadata for ingested documents (10-K filings and rulebooks)."""
    doc_id: str = Field(..., description="Unique document ID (e.g. MSFT_10K_2025)")
    company: str
    ticker: str
    sector: str
    doc_type: str = Field("10-K", description="'10-K' or 'RULEBOOK'")
    fiscal_year: Optional[int] = None
    filing_date: Optional[str] = None
    source_url: str
    checksum: str = Field(..., description="SHA-256 hash of raw document for idempotency")
    file_path: str
    downloaded_at: datetime = Field(default_factory=datetime.utcnow)


class ParsedSection(BaseModel):
    """Extracted narrative section from an annual report or rulebook chapter."""
    section_id: str = Field(..., description="e.g. MSFT_10K_2025_item_1a")
    doc_id: str
    company: str
    ticker: str
    fiscal_year: Optional[int] = None
    section_name: str
    section_code: str
    raw_text: str
    clean_text: str
    token_count: int
    char_count: int
    garbage_ratio: float


class Chunk(BaseModel):
    """Text chunk prepared for embedding and retrieval."""
    chunk_id: str = Field(..., description="Unique chunk ID (e.g. MSFT_10K_2025_item_1a_c001)")
    doc_id: str
    section_id: str
    company: str
    ticker: str
    fiscal_year: Optional[int] = None
    section_name: str
    position: int
    text: str
    context_header: Optional[str] = None
    token_count: int


class RetrievedChunk(BaseModel):
    """A chunk retrieved by the search pipeline with ranking and explainability scores."""
    chunk: Chunk
    dense_score: Optional[float] = None
    dense_rank: Optional[int] = None
    sparse_score: Optional[float] = None
    sparse_rank: Optional[int] = None
    rrf_score: Optional[float] = None
    rerank_score: Optional[float] = None
    final_rank: int


class Citation(BaseModel):
    """Citation linking a generated claim back to an exact context chunk."""
    tag: str = Field(..., description="Citation marker, e.g. '[1]'")
    chunk_id: str
    company: str
    ticker: str
    fiscal_year: Optional[int] = None
    section_name: str
    snippet: str
    is_valid: bool = True


class QueryFilters(BaseModel):
    """Extracted metadata filters for targeted search."""
    company: Optional[str] = None
    ticker: Optional[str] = None
    fiscal_year: Optional[int] = None
    doc_type: Optional[str] = None
    section_name: Optional[str] = None


class AnswerResponse(BaseModel):
    """Final grounded assistant response."""
    query: str
    answer: str
    is_refusal: bool
    citations: List[Citation] = []
    retrieved_chunks: List[RetrievedChunk] = []
    latency_ms: Dict[str, float] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)
