"""
Unified Hybrid Retriever for DocLens.
Combines Dense Vector Retrieval (BGE), Sparse BM25, Reciprocal Rank Fusion,
and Cross-Encoder Reranking, with automatic query filter extraction.
"""
import re
import time
from typing import Dict, List, Optional, Tuple

from src.common.config import Config, load_config
from src.common.logger import get_logger
from src.common.models import Chunk, QueryFilters, RetrievedChunk
from src.retrieval.dense_indexer import DenseVectorIndexer
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.reranker import CrossEncoderReranker
from src.retrieval.sparse_indexer import SparseBM25Indexer

logger = get_logger("hybrid_retriever")

COMPANY_MAPPINGS = {
    "microsoft": "MSFT",
    "msft": "MSFT",
    "apple": "AAPL",
    "aapl": "AAPL",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "chase": "JPM",
    "jpm": "JPM",
    "goldman": "GS",
    "sachs": "GS",
    "goldman sachs": "GS",
    "gs": "GS",
    "pfizer": "PFE",
    "pfe": "PFE",
    "exxon": "XOM",
    "mobil": "XOM",
    "exxonmobil": "XOM",
    "xom": "XOM",
    "sebi": "SEBI",
    "lodr": "SEBI",
}


def extract_query_filters(query: str) -> QueryFilters:
    """Extract company ticker, fiscal year, and regulation filters from user query."""
    q_lower = query.lower()
    ticker = None
    for name, sym in COMPANY_MAPPINGS.items():
        if re.search(r"\b" + re.escape(name) + r"\b", q_lower):
            ticker = sym
            break

    # Extract 4-digit fiscal year
    year = None
    year_match = re.search(r"\b(20[12][0-9])\b", query)
    if year_match:
        year = int(year_match.group(1))

    return QueryFilters(ticker=ticker, fiscal_year=year)


class HybridRetriever:
    """Multi-stage hybrid retrieval engine with ablation configuration flags."""

    def __init__(
        self,
        config: Optional[Config] = None,
        dense_indexer: Optional[DenseVectorIndexer] = None,
        sparse_indexer: Optional[SparseBM25Indexer] = None,
        reranker: Optional[CrossEncoderReranker] = None,
    ):
        self.config = config or load_config()
        self.dense = dense_indexer or DenseVectorIndexer(self.config)
        self.sparse = sparse_indexer or SparseBM25Indexer(self.config.bm25_index_path)
        self.reranker = reranker or CrossEncoderReranker(self.config.reranker_model)

    def search(
        self,
        query: str,
        filters: Optional[QueryFilters] = None,
        use_sparse: bool = True,
        use_reranker: bool = True,
        use_filters: bool = True,
        top_k: int = 5,
    ) -> Tuple[List[RetrievedChunk], Dict[str, float]]:
        """
        Execute multi-stage retrieval with latency profiling.

        Args:
            query: The user question.
            filters: Optional metadata filters. If None and use_filters is True, inferred automatically.
            use_sparse: Whether to perform BM25 keyword search and fuse.
            use_reranker: Whether to run cross-encoder reranking.
            use_filters: Whether to apply metadata filtering.
            top_k: Final number of chunks to return.
        """
        latencies: Dict[str, float] = {}

        if use_filters and filters is None:
            filters = extract_query_filters(query)
        elif not use_filters:
            filters = None

        # 1. Dense Vector Retrieval
        t0 = time.perf_counter()
        dense_results = self.dense.search(
            query=query,
            filters=filters,
            top_k=self.config.top_k_dense,
        )
        latencies["dense_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # Map chunks by chunk_id
        chunk_pool: Dict[str, Chunk] = {c.chunk_id: c for c, _, _ in dense_results}
        dense_scores: Dict[str, float] = {c.chunk_id: s for c, s, _ in dense_results}
        dense_ranks: Dict[str, int] = {c.chunk_id: r for c, _, r in dense_results}

        sparse_scores: Dict[str, float] = {}
        sparse_ranks: Dict[str, int] = {}

        # 2. Sparse BM25 Retrieval (if enabled)
        if use_sparse:
            t1 = time.perf_counter()
            sparse_results = self.sparse.search(
                query=query,
                filters=filters,
                top_k=self.config.top_k_sparse,
            )
            latencies["sparse_ms"] = round((time.perf_counter() - t1) * 1000.0, 2)

            for c, s, r in sparse_results:
                chunk_pool[c.chunk_id] = c
                sparse_scores[c.chunk_id] = s
                sparse_ranks[c.chunk_id] = r

            # 3. Reciprocal Rank Fusion
            t2 = time.perf_counter()
            rankings = [
                [c.chunk_id for c, _, _ in dense_results],
                [c.chunk_id for c, _, _ in sparse_results],
            ]
            fused_list = reciprocal_rank_fusion(rankings, k=self.config.rrf_k)
            latencies["fusion_ms"] = round((time.perf_counter() - t2) * 1000.0, 2)

            candidate_cids = [cid for cid, _ in fused_list]
            rrf_score_map = dict(fused_list)
        else:
            candidate_cids = [c.chunk_id for c, _, _ in dense_results]
            rrf_score_map = {}

        candidate_chunks = [chunk_pool[cid] for cid in candidate_cids if cid in chunk_pool]

        # 4. Cross-Encoder Reranker (if enabled)
        rerank_scores: Dict[str, float] = {}
        if use_reranker and candidate_chunks:
            # Score top 20 candidates with cross-encoder
            candidates_to_rerank = candidate_chunks[:20]
            scored_candidates, rerank_lat = self.reranker.rerank(
                query=query,
                chunks=candidates_to_rerank,
                top_k=top_k,
            )
            latencies["rerank_ms"] = rerank_lat
            final_chunks = [c for c, _ in scored_candidates]
            for c, s in scored_candidates:
                rerank_scores[c.chunk_id] = s
        else:
            final_chunks = candidate_chunks[:top_k]

        # Build explainable RetrievedChunk list
        results: List[RetrievedChunk] = []
        for rank, ch in enumerate(final_chunks, start=1):
            results.append(
                RetrievedChunk(
                    chunk=ch,
                    dense_score=dense_scores.get(ch.chunk_id),
                    dense_rank=dense_ranks.get(ch.chunk_id),
                    sparse_score=sparse_scores.get(ch.chunk_id),
                    sparse_rank=sparse_ranks.get(ch.chunk_id),
                    rrf_score=rrf_score_map.get(ch.chunk_id),
                    rerank_score=rerank_scores.get(ch.chunk_id),
                    final_rank=rank,
                )
            )

        latencies["total_retrieval_ms"] = round(sum(latencies.values()), 2)
        return results, latencies
