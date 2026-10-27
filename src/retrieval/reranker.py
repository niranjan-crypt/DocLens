"""
Cross-Encoder Reranker for DocLens.
Uses cross-encoder/ms-marco-MiniLM-L-6-v2 to compute joint query-document relevance scores
and rerank top candidate chunks.
"""
import time
from typing import List, Optional, Tuple
from sentence_transformers import CrossEncoder

from src.common.config import Config, load_config
from src.common.logger import get_logger
from src.common.models import Chunk

logger = get_logger("reranker")


class CrossEncoderReranker:
    """Scores (query, chunk) candidate pairs using cross-encoder architecture."""

    def __init__(self, model_name: Optional[str] = None):
        cfg = load_config()
        self.model_name = model_name or cfg.reranker_model
        self._model = None

    @property
    def model(self):
        if self._model is None:
            logger.info(f"Loading Cross-Encoder model: {self.model_name}...")
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int = 5,
    ) -> Tuple[List[Tuple[Chunk, float]], float]:
        """
        Rerank a candidate list of chunks against the query.

        Returns:
            Tuple of (ranked_chunks_with_scores, latency_ms).
        """
        if not chunks:
            return [], 0.0

        t0 = time.perf_counter()
        pairs = [[query, chunk.text] for chunk in chunks]
        scores = self.model.predict(pairs)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Pair scores with chunks
        scored_chunks = list(zip(chunks, [float(s) for s in scores]))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        return scored_chunks[:top_k], round(latency_ms, 2)
