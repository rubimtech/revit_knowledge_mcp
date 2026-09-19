"""Semantic knowledge search tool."""

import logging

from ..deps import Deps
from .common import collect_semantic, dumps, hits_to_dicts

log = logging.getLogger(__name__)


def register_knowledge_tools(mcp, deps: Deps) -> None:
    @mcp.tool()
    def search_knowledge(
        query: str,
        collections: list[str] | None = None,
        platform: str | None = None,
        limit: int = 5,
        max_results: int = 20,
        backends: list[str] | None = None,
        score_threshold: float = 0.0,
    ) -> str:
        """Semantic search across the local knowledge base.

        Use for natural-language questions about Revit, Navisworks or Archicad
        APIs, SDK samples and pyRevit code. Searches pre-embedded Qdrant
        collections (bge-m3) and, when configured, an OpenAI vector store.

        Args:
            query: Natural-language search query.
            collections: Restrict to specific collections (default: all enabled).
            platform: Restrict by platform: revit, navisworks, archicad, other.
            limit: Max results per collection/backend.
            max_results: Max results returned after ranking.
            backends: Backends to query: qdrant, openai (default: all available).
            score_threshold: Minimum score for the OpenAI backend (0.0-1.0).

        Returns:
            JSON with query, chosen backends, ranked results and any errors.
        """
        ranked, chosen, errors = collect_semantic(
            deps,
            query,
            collections=collections,
            platform=platform,
            limit=limit,
            backends=backends,
            score_threshold=score_threshold,
        )
        ranked = ranked[: max(1, max_results)]
        return dumps(
            {
                "query": query,
                "backends": chosen,
                "platform": platform,
                "count": len(ranked),
                "results": hits_to_dicts(ranked),
                "errors": errors,
            }
        )
