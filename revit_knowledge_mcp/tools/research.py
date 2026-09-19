"""Composite research tool: semantic discovery + live documentation."""

import logging
import re

from ..backends import SearchHit
from ..deps import Deps
from ..sources.rvtdocs import RvtdocsError
from .common import collect_semantic, dumps, hits_to_dicts

log = logging.getLogger(__name__)

TYPE_SUFFIX = re.compile(
    r"\s+(Class|Method|Property|Properties|Methods|Enumeration Member|Enumeration|"
    r"Interface|Structure|Delegate|Event|Field|Operator|Constructor|Remarks)$",
    re.IGNORECASE,
)
UUID = re.compile(r"^[0-9a-fA-F-]{32,36}$")


def _clean_entity(title: str) -> str:
    candidate = TYPE_SUFFIX.sub("", title.strip())
    if "(" not in candidate and "." in candidate:
        candidate = candidate.rsplit(".", 1)[-1]
    candidate = candidate.strip()
    if not candidate or UUID.match(candidate):
        return ""
    if not re.match(r"^[A-Za-z_]", candidate):
        return ""
    return candidate


def _candidate_entities(hits: list[SearchHit], registry, max_entities: int) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        if hit.source != "qdrant":
            continue
        info = registry.get(hit.collection or "")
        if info is not None and info.platform != "revit":
            continue
        candidate = _clean_entity(hit.title)
        if not candidate:
            continue
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
        if len(candidates) >= max_entities:
            break
    return candidates


def _matches_entity(entity: str, hit: SearchHit) -> bool:
    """Check that a documentation hit actually refers to the requested entity."""
    key = entity.rsplit(".", 1)[-1].split("(")[0].strip().lower()
    if not key:
        return False
    return key in (hit.title or "").lower()


def register_research_tools(mcp, deps: Deps) -> None:
    @mcp.tool()
    def research(
        query: str,
        platform: str | None = None,
        collections: list[str] | None = None,
        limit: int = 5,
        docs: int = 3,
        year: int | None = None,
        include_docs: bool = True,
    ) -> str:
        """Semantic discovery followed by authoritative documentation.

        Runs a semantic search over the knowledge base, extracts the most
        relevant Revit API entity names, then fetches their official rvtdocs.com
        pages. Use this for "how do I do X in the Revit API" questions where you
        want both examples/context and the exact API contract.

        Args:
            query: Natural-language question or topic.
            platform: Restrict semantic search to a platform (revit, navisworks, archicad).
            collections: Restrict to specific knowledge collections.
            limit: Max semantic results per collection/backend.
            docs: How many entities to enrich with full documentation (0 disables).
            year: Revit API year for documentation lookup (default from config).
            include_docs: Set false to get semantic results only.

        Returns:
            JSON with ranked semantic results, fetched API documentation and errors.
        """
        ranked, chosen, errors = collect_semantic(
            deps,
            query,
            collections=collections,
            platform=platform,
            limit=limit,
        )

        api_docs = []
        wanted = max(0, docs) if include_docs else 0
        if wanted:
            if not deps.rvtdocs.available():
                errors.append("rvtdocs: backend disabled, skipping documentation")
            else:
                for entity in _candidate_entities(ranked, deps.registry, wanted):
                    try:
                        matches = deps.rvtdocs.search(entity, limit=3, year=year)
                    except RvtdocsError as exc:
                        errors.append(f"rvtdocs lookup '{entity}': {exc}")
                        continue
                    if not matches:
                        continue
                    best = next((hit for hit in matches if _matches_entity(entity, hit)), None)
                    if best is None:
                        errors.append(f"rvtdocs: no confident match for '{entity}'")
                        continue
                    try:
                        markdown = deps.rvtdocs.fetch_markdown(best.metadata["slug"])
                    except (RvtdocsError, KeyError) as exc:
                        errors.append(f"rvtdocs fetch '{entity}': {exc}")
                        continue
                    api_docs.append(
                        {
                            "entity": entity,
                            "title": best.title,
                            "type": best.kind,
                            "url": best.url,
                            "markdown": markdown,
                        }
                    )

        return dumps(
            {
                "query": query,
                "backends": chosen,
                "semantic": hits_to_dicts(ranked, snippet_limit=400),
                "api_docs": api_docs,
                "errors": errors,
            }
        )
