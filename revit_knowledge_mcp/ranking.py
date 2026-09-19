"""Result fusion helpers.

Qdrant cosine scores and OpenAI vector-store scores are not directly
comparable, so cross-backend results are combined with Reciprocal Rank Fusion
(RRF) instead of raw score sorting.
"""

from .backends.base import SearchHit

RRF_K = 60


def fuse(hit_lists: list[list[SearchHit]], k: int = RRF_K) -> list[SearchHit]:
    """Merge ranked hit lists using Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    hits: dict[str, SearchHit] = {}

    for hit_list in hit_lists:
        for rank, hit in enumerate(hit_list, start=1):
            key = hit.key()
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            hits.setdefault(key, hit)

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    result: list[SearchHit] = []
    for key, score in ordered:
        hit = hits[key]
        hit.rrf = round(score, 6)
        result.append(hit)
    return result
