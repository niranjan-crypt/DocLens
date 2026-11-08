"""
Dual Indexing Runner for DocLens (Week 2 / Phases 4-6).
Embeds chunks into ChromaDB with BGE embeddings,
builds the BM25 exact keyword index, and performs smoke retrieval tests.
"""
import json
import sys
import time
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.common.config import Config, load_config
from src.common.logger import get_logger
from src.common.models import Chunk
from src.retrieval.dense_indexer import DenseVectorIndexer
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.sparse_indexer import SparseBM25Indexer

logger = get_logger("build_indexes")


def build_all_indexes():
    config: Config = load_config()
    processed_dir = Path(config.processed_dir)
    chunks_file = processed_dir / "chunks.jsonl"

    if not chunks_file.exists():
        print(f"❌ Error: Chunks file not found at {chunks_file}. Run scripts/run_ingestion.py first.")
        sys.exit(1)

    print("=" * 65)
    print("⚡ DOCLENS DUAL INDEXING & RETRIEVAL PIPELINE (WEEK 2)")
    print("=" * 65)

    # 1. Load Chunks
    chunks: List[Chunk] = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(Chunk(**json.loads(line)))

    print(f"\n[Step 1/3] Loaded {len(chunks)} chunks from {chunks_file}.")

    # 2. Build Sparse BM25 Index
    print("\n[Step 2/3] Building & Persisting BM25 Index...")
    t0 = time.perf_counter()
    sparse_indexer = SparseBM25Indexer(config.bm25_index_path)
    sparse_indexer.build_index(chunks)
    sparse_time = (time.perf_counter() - t0) * 1000.0
    print(f"  ✓ BM25 Index successfully serialized to {config.bm25_index_path} ({sparse_time:.1f} ms)")

    # 3. Build Dense ChromaDB Collection
    print("\n[Step 3/3] Generating BGE Embeddings & Indexing into ChromaDB...")
    t0 = time.perf_counter()
    dense_indexer = DenseVectorIndexer(config)
    dense_indexer.index_chunks(chunks)
    dense_time = (time.perf_counter() - t0) * 1000.0
    print(f"  ✓ ChromaDB index successfully updated at {config.chroma_db_dir} ({dense_time:.1f} ms)")

    # 4. Smoke Test Queries
    print("\n" + "-" * 65)
    print("🔍 Running Smoke Test Searches...")
    print("-" * 65)

    retriever = HybridRetriever(config, dense_indexer=dense_indexer, sparse_indexer=sparse_indexer)
    smoke_queries = [
        "What are the primary operational revenue segments of Microsoft?",
        "What does SEBI LODR Regulation 30 mandate regarding disclosure of material events?",
        "What are Pfizer's primary biopharmaceutical commercial segments?",
    ]

    for q in smoke_queries:
        print(f"\nQuery: '{q}'")
        results, latencies = retriever.search(q, top_k=3)
        print(f"  Latency breakdown: Vector={latencies.get('dense_vector_ms', 0):.1f}ms, BM25={latencies.get('sparse_bm25_ms', 0):.1f}ms, Fusion={latencies.get('rrf_fusion_ms', 0):.1f}ms, Rerank={latencies.get('cross_encoder_rerank_ms', 0):.1f}ms")
        for i, res in enumerate(results, start=1):
            ch = res.chunk
            print(f"  [{i}] Doc: {ch.doc_id} | Section: {ch.section_name} | Dense: {res.dense_score:.3f} | BM25: {res.sparse_score:.3f} | Rerank: {res.rerank_score:.3f}")
            print(f"      Text: {ch.text[:100]}...")

    print("\n" + "=" * 65)
    print("✨ WEEK 2 PIPELINE COMPLETE: Dense & Sparse Indexes Built & Verified!")
    print("=" * 65)


if __name__ == "__main__":
    build_all_indexes()
