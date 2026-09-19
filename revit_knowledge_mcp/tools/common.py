"""Helpers shared by the tool registrars."""

import json
import logging
from typing import Any

from ..backends import QdrantUnavailable, SearchHit
from ..deps import Deps
from ..ranking import fuse

log = logging.getLogger(__name__)


def dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def collect_semantic(
    deps: Deps,
    query: str,
    collections: list[str] | None = None,
    platform: str | None = None,
    limit: int = 5,
    backends: list[str] | None = None,
    score_threshold: float = 0.0,
) -> tuple[list[SearchHit], list[str], list[str]]:
    """Run semantic backends and return (ranked_hits, chosen_backends, errors)."""
    errors: list[str] = []
    hit_lists: list[list[SearchHit]] = []
    chosen: list[str] = []

    if backends:
        requested = [name.lower().strip() for name in backends]
        for name in requested:
            if name in ("qdrant", "openai"):
                chosen.append(name)
            else:
                errors.append(f"unknown backend '{name}' (allowed: qdrant, openai)")
    else:
        chosen.append("qdrant")
        if deps.openai.available():
            chosen.append("openai")

    if "qdrant" in chosen:
        try:
            grouped, qdrant_errors = deps.qdrant.search_grouped(
                query, limit=limit, collections=collections, platform=platform
            )
            for hits in grouped.values():
                hit_lists.append(hits)
            errors.extend(f"qdrant/{message}" for message in qdrant_errors)
        except QdrantUnavailable as exc:
            errors.append(f"qdrant: {exc}")

    if "openai" in chosen:
        if deps.openai.available():
            try:
                hits = deps.openai.search(
                    query, limit=limit, score_threshold=score_threshold
                )
                if hits:
                    hit_lists.append(hits)
            except Exception as exc:  # pragma: no cover - network dependent
                errors.append(f"openai: {exc}")
        else:
            errors.append(
                "openai: not configured (set OPENAI_API_KEY and OPENAI_VECTOR_STORE_ID)"
            )

    flat = [hit for hits in hit_lists for hit in hits]
    if not flat:
        ranked: list[SearchHit] = []
    elif len(hit_lists) <= 1 or all(hit.source == "qdrant" for hit in flat):
        ranked = sorted(flat, key=lambda hit: hit.score or 0.0, reverse=True)
    else:
        ranked = fuse(hit_lists)
    return _dedupe(ranked), chosen, errors


def _dedupe(hits: list[SearchHit]) -> list[SearchHit]:
    """Drop exact duplicates (same title and snippet) keeping the best rank."""
    seen: set[tuple[str, str, str, str]] = set()
    result: list[SearchHit] = []
    for hit in hits:
        key = (hit.source, hit.collection or "", hit.title, hit.snippet)
        if key in seen:
            continue
        seen.add(key)
        result.append(hit)
    return result


def hits_to_dicts(hits: list[SearchHit], snippet_limit: int = 500) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for rank, hit in enumerate(hits, start=1):
        item = hit.to_dict(snippet_limit=snippet_limit)
        item["rank"] = rank
        results.append(item)
    return results
