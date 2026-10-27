"""
Reciprocal Rank Fusion (RRF) for DocLens.
Merges dense vector rankings and sparse BM25 keyword rankings
into an optimal hybrid ranking without requiring score scale normalization.
"""
from typing import Dict, List, Tuple


def reciprocal_rank_fusion(
    rankings: List[List[str]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """
    Compute Reciprocal Rank Fusion scores over multiple ranked lists of chunk IDs.

    Args:
        rankings: List of rankings, where each ranking is a list of chunk IDs ordered best-to-worst.
        k: Smoothing constant (standard literature default is 60).

    Returns:
        List of (chunk_id, rrf_score) tuples sorted in descending order of score.
    """
    scores: Dict[str, float] = {}

    for ranking in rankings:
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank))

    sorted_ranks = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return sorted_ranks
