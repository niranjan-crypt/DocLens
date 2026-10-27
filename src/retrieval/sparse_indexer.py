"""
Sparse BM25 Indexer for DocLens.
Uses BM25Okapi to index chunks with domain-aware tokenization
(preserving regulation numbers, section headers, and tickers).
"""
import pickle
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rank_bm25 import BM25Okapi

from src.common.config import Config, load_config
from src.common.logger import get_logger
from src.common.models import Chunk, QueryFilters

logger = get_logger("sparse_indexer")


def tokenize_for_bm25(text: str) -> List[str]:
    """Domain-aware tokenizer that lowercases while preserving tokens like 'regulation 30', '10-k', 'item 1a'."""
    text_clean = text.lower()
    # Replace dashes in 10-k so it stays a single token
    text_clean = re.sub(r"\b10-k\b", "10k", text_clean)
    # Extract alphanumeric words and numbers
    tokens = re.findall(r"[a-z0-9]+", text_clean)
    return tokens


class SparseBM25Indexer:
    """Manages BM25 keyword index creation, persistence, and querying."""

    def __init__(self, index_path: Optional[Path] = None):
        cfg = load_config()
        self.index_path = Path(index_path or cfg.bm25_index_path)
        self.bm25: Optional[BM25Okapi] = None
        self.chunks: List[Chunk] = []
        self.chunk_map: Dict[str, Chunk] = {}

    def build_index(self, chunks: List[Chunk]):
        """Build BM25 index over provided chunk objects and serialize to disk."""
        self.chunks = chunks
        self.chunk_map = {c.chunk_id: c for c in chunks}

        tokenized_corpus = [tokenize_for_bm25(c.text) for c in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

        self.save()
        logger.info(f"Built and saved BM25 index with {len(chunks)} chunks to {self.index_path}")

    def save(self):
        """Serialize index and chunk catalog to pickle."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "wb") as f:
            pickle.dump({"bm25": self.bm25, "chunks": self.chunks}, f)

    def load(self) -> bool:
        """Load persisted BM25 index from disk."""
        if not self.index_path.exists():
            logger.warning(f"No BM25 index found at {self.index_path}")
            return False
        with open(self.index_path, "rb") as f:
            data = pickle.load(f)
            self.bm25 = data["bm25"]
            self.chunks = data["chunks"]
            self.chunk_map = {c.chunk_id: c for c in self.chunks}
        logger.info(f"Loaded BM25 index with {len(self.chunks)} chunks from {self.index_path}")
        return True

    def search(
        self,
        query: str,
        filters: Optional[QueryFilters] = None,
        top_k: int = 20,
    ) -> List[Tuple[Chunk, float, int]]:
        """
        Query BM25 index, optionally applying metadata pre-filtering.

        Returns:
            List of (chunk, score, rank) tuples.
        """
        if self.bm25 is None and not self.load():
            raise RuntimeError("BM25 index is not initialized or loaded.")

        query_tokens = tokenize_for_bm25(query)
        if not query_tokens:
            return []

        doc_scores = self.bm25.get_scores(query_tokens)

        # Pair scores with chunks
        ranked_items = []
        for idx, score in enumerate(doc_scores):
            chunk = self.chunks[idx]

            # Apply metadata filters if provided
            if filters:
                if filters.ticker and chunk.ticker.upper() != filters.ticker.upper():
                    continue
                if filters.company and filters.company.lower() not in chunk.company.lower():
                    continue
                if filters.fiscal_year and chunk.fiscal_year != filters.fiscal_year:
                    continue

            ranked_items.append((chunk, float(score)))

        # Sort descending by score
        ranked_items.sort(key=lambda x: x[1], reverse=True)

        # Assign rank and take top_k
        results = [
            (chunk, score, rank)
            for rank, (chunk, score) in enumerate(ranked_items[:top_k], start=1)
        ]
        return results
