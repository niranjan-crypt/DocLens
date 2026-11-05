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


