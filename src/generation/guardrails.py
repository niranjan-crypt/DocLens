"""
Guardrails and Refusal Enforcement for DocLens.
Enforces score-threshold refusals to stop hallucination before generation,
and appends regulatory/financial compliance disclaimers.
"""
from typing import List, Optional, Tuple
from src.common.config import Config, load_config
from src.common.models import RetrievedChunk

DISCLAIMER = "\n\n*(Notice: DocLens responses are citation-grounded research summaries for educational/compliance review and do not constitute formal investment, legal, or regulatory advice.)*"


class GenerationGuardrails:
    """Enforces evidence sufficiency thresholds and regulatory refusal mechanics."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.refusal_threshold = self.config.refusal_score_threshold
        self.canonical_refusal = self.config.refusal_message

    def evaluate_retrieval_evidence(
        self,
        retrieved_chunks: List[RetrievedChunk],
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate if retrieved chunks meet minimum evidence threshold.

        Returns:
            Tuple of (is_sufficient, refusal_reason).
            If False, generation should be skipped immediately.
        """
        if not retrieved_chunks:
            return False, "Zero documents retrieved for the provided query."

        top_chunk = retrieved_chunks[0]

        # Check cross-encoder rerank score if available
        if top_chunk.rerank_score is not None:
            # Cross-encoder scores typically range -10 to +10; threshold around -2.0 or config
            if top_chunk.rerank_score < -2.0:
                return False, f"Top rerank relevance score ({top_chunk.rerank_score:.2f}) below confidence threshold."
        elif top_chunk.dense_score is not None:
            # Cosine similarity threshold
            if top_chunk.dense_score < self.refusal_threshold:
                return False, f"Top dense similarity score ({top_chunk.dense_score:.2f}) below threshold ({self.refusal_threshold})."

        return True, None

    def is_refusal_answer(self, text: str) -> bool:
        """Detect whether the model response signifies a refusal."""
        t_low = text.lower()
        phrases = [
            "do not contain enough information",
            "does not contain enough information",
            "insufficient information",
            "not mentioned in the provided",
            "no information provided",
        ]
        return any(p in t_low for p in phrases)

    def format_final_answer(self, raw_answer: str, is_refusal: bool) -> str:
        """Append standing regulatory compliance note to generated responses."""
        if is_refusal:
            return self.canonical_refusal
        return f"{raw_answer.strip()}{DISCLAIMER}"
