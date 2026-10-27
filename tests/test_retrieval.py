"""
Tests for Retrieval, Filtering, and Reciprocal Rank Fusion.
"""
from src.common.models import QueryFilters
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.hybrid_retriever import extract_query_filters
from src.retrieval.sparse_indexer import tokenize_for_bm25


def test_query_filter_extractor():
    # Ticker and year extraction
    filters = extract_query_filters("What are Pfizer's primary biopharmaceutical risk factors in 2025?")
    assert filters.ticker == "PFE"
    assert filters.fiscal_year == 2025

    # Apple with 2024
    filters2 = extract_query_filters("Summarize Apple's supply chain disclosures from 2024")
    assert filters2.ticker == "AAPL"
    assert filters2.fiscal_year == 2024


def test_reciprocal_rank_fusion():
    ranking_dense = ["chunk_A", "chunk_B", "chunk_C"]
    ranking_sparse = ["chunk_B", "chunk_A", "chunk_D"]

    fused = reciprocal_rank_fusion([ranking_dense, ranking_sparse], k=60)
    # chunk_A: 1/(60+1) + 1/(60+2) = 1/61 + 1/62
    # chunk_B: 1/(60+2) + 1/(60+1) = 1/62 + 1/61 (identical score, both tied for top)
    top_two = [cid for cid, _ in fused[:2]]
    assert "chunk_A" in top_two
    assert "chunk_B" in top_two
    # chunk_C and chunk_D appear after
    assert fused[2][0] in ["chunk_C", "chunk_D"]


def test_bm25_tokenizer_preserves_identifiers():
    tokens = tokenize_for_bm25("Regulation 30 under SEBI LODR 2015 and Item 1A in 10-K filing")
    assert "regulation" in tokens
    assert "30" in tokens
    assert "sebi" in tokens
    assert "lodr" in tokens
    assert "10k" in tokens
