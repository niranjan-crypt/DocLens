"""
FastAPI Production REST Service for DocLens.
Provides endpoints for question answering, document lineage queries, health check, and feedback.
"""
import json
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
)
from src.common.config import Config, load_config
from src.common.db import DatabaseManager
from src.common.logger import get_logger
from src.common.models import DocumentMetadata, QueryFilters
from src.generation.llm_client import LLMClient
from src.retrieval.hybrid_retriever import HybridRetriever

logger = get_logger("api_main")

app = FastAPI(
    title="DocLens API",
    description="A Citation-Grounded Question Answering Assistant over Company 10-K Filings and Disclosure Rules",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config: Config = load_config()
db = DatabaseManager(config.db_url)
_retriever = None
_llm = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(config)
    return _retriever


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient(config)
    return _llm


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health status and telemetry."""
    docs = db.list_documents()
    return HealthResponse(
        status="healthy",
        version=config.version,
        database_connected=True,
        total_indexed_documents=len(docs),
        models={
            "embedding": config.embedding_model,
            "reranker": config.reranker_model,
            "generator": config.llm_model,
        },
    )


@app.get("/documents", response_model=List[DocumentMetadata])
def list_documents():
    """Return all ingested annual filings and regulatory rulebooks with lineage checksums."""
    return db.list_documents()


@app.post("/ask", response_model=QueryResponse)
def ask_question(request: QueryRequest):
    """
    Execute hybrid retrieval, cross-encoder reranking, and citation-grounded generation.
    Logs query and latency to PostgreSQL/SQLite registry.
    """
    filters = None
    if request.ticker or request.fiscal_year:
        filters = QueryFilters(ticker=request.ticker, fiscal_year=request.fiscal_year)

    # 1. Multi-stage Hybrid Retrieval
    retriever_instance = get_retriever()
    retrieved_chunks, ret_latencies = retriever_instance.search(
        query=request.query,
        filters=filters,
        use_sparse=request.use_sparse,
        use_reranker=request.use_reranker,
        use_filters=(filters is not None),
        top_k=config.final_top_k,
    )

    # 2. Grounded Generation & Citation Verification
    llm_instance = get_llm()
    response = llm_instance.generate_answer(
        query=request.query,
        retrieved_chunks=retrieved_chunks,
        prior_latencies=ret_latencies,
    )

    # 3. Log to database
    chunk_ids_json = json.dumps([r.chunk.chunk_id for r in retrieved_chunks])
    total_latency = response.latency_ms.get("total_pipeline_ms", 0.0)
    log_id = db.log_query(
        query=request.query,
        answer=response.answer,
        is_refusal=response.is_refusal,
        latency_ms=total_latency,
        chunk_ids=chunk_ids_json,
    )

    return QueryResponse(
        query_log_id=log_id,
        query=response.query,
        answer=response.answer,
        is_refusal=response.is_refusal,
        citations=response.citations,
        retrieved_chunks=response.retrieved_chunks,
        latencies=response.latency_ms,
    )


@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest):
    """Store user rating (Thumbs Up: 1, Thumbs Down: -1) for continuous monitoring."""
    db.record_feedback(request.query_log_id, request.rating)
    return FeedbackResponse(
        status="success",
        message=f"Feedback recorded for query log #{request.query_log_id}",
    )
