"""
Evaluation Metrics Harness for DocLens.
Implements Recall@k, Mean Reciprocal Rank (MRR), Citation Validity,
and Refusal Accuracy in clean Python without bloated dependencies.
"""
from typing import List, Set


def recall_at_k(retrieved_ids: List[str], gold_ids: List[str], k: int = 5) -> float:
    """
    Compute Recall@k.
    Returns 1.0 if any gold chunk/section ID appears in the top-k retrieved list, else 0.0.
    """
    if not gold_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    for g in gold_ids:
        # Check either exact match or section prefix match (e.g. MSFT_10K_2025_item_1a in chunk_id)
        if any(g.lower() in r.lower() for r in top_k):
            return 1.0
    return 0.0


def mrr(retrieved_ids: List[str], gold_ids: List[str]) -> float:
    """
    Compute Mean Reciprocal Rank (MRR).
    Returns 1 / rank of the first relevant gold chunk retrieved (1-indexed).
    """
    if not gold_ids:
        return 0.0
    for rank, cid in enumerate(retrieved_ids, start=1):
        if any(g.lower() in cid.lower() for g in gold_ids):
            return 1.0 / rank
    return 0.0


def citation_validity_score(total_citations: int, valid_citations: int) -> float:
    """Share of generated citation tags that point to actual valid context chunks."""
    if total_citations == 0:
        return 1.0
    return round(valid_citations / total_citations, 4)


def refusal_accuracy(
    is_refusal: bool,
    is_unanswerable_gold: bool,
) -> float:
    """
    Compute refusal accuracy:
    - 1.0 if unanswerable query was correctly refused
    - 1.0 if answerable query was NOT refused
    - 0.0 on false refusal or hallucination of an answer when evidence was missing
    """
    if is_unanswerable_gold and is_refusal:
        return 1.0
    if not is_unanswerable_gold and not is_refusal:
        return 1.0
    return 0.0
