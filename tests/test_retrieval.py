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


def test_sparse_bm25_indexer():
    import tempfile
    from pathlib import Path
    from src.common.models import Chunk
    from src.retrieval.sparse_indexer import SparseBM25Indexer

    chunks = [
        Chunk(
            chunk_id="c1",
            doc_id="d1",
            section_id="s1",
            company="Pfizer",
            ticker="PFE",
            fiscal_year=2025,
            section_name="Item 1. Business",
            position=0,
            text="Pfizer develops innovative oncology and vaccine treatments.",
            token_count=10,
        ),
        Chunk(
            chunk_id="c2",
            doc_id="d2",
            section_id="s2",
            company="Microsoft",
            ticker="MSFT",
            fiscal_year=2025,
            section_name="Item 1. Business",
            position=0,
            text="Microsoft powers enterprise cloud computing and Azure AI services.",
            token_count=10,
        ),
        Chunk(
            chunk_id="c3",
            doc_id="d3",
            section_id="s3",
            company="ExxonMobil",
            ticker="XOM",
            fiscal_year=2025,
            section_name="Item 1. Business",
            position=0,
            text="ExxonMobil explores for crude oil and produces refined petroleum products.",
            token_count=10,
        ),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        idx_path = Path(tmpdir) / "bm25_test.pkl"
        indexer = SparseBM25Indexer(idx_path)
        indexer.build_index(chunks)
        assert idx_path.exists()

        results = indexer.search("oncology vaccine", top_k=2)
        assert len(results) > 0
        top_chunk, score, rank = results[0]
        assert top_chunk.chunk_id == "c1"
        assert score > 0

