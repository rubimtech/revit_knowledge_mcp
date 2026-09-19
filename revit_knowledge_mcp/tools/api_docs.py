"""Live Revit API documentation tools (lookup + retrieval)."""

import logging

from ..deps import Deps
from ..sources.rvtdocs import RvtdocsError, page_url
from .common import dumps

log = logging.getLogger(__name__)

ALLOWED_TYPES = (
    "class",
    "interface",
    "enum",
    "structure",
    "delegate",
    "method",
    "property",
    "event",
    "constructor",
    "field",
    "operator",
)


def _normalize_types(types: list[str] | None) -> list[str] | None:
    if not types:
        return None
    normalized = []
    for value in types:
        lowered = value.strip().lower()
        if lowered in ALLOWED_TYPES and lowered not in normalized:
            normalized.append(lowered)
    return normalized or None


def register_api_docs_tools(mcp, deps: Deps) -> None:
    @mcp.tool()
    def lookup_api(
        query: str,
        year: int | None = None,
        types: list[str] | None = None,
        limit: int = 10,
    ) -> str:
        """Find Revit API entities in the official rvtdocs.com index.

        Use to discover the exact class, method, property, event, enum or
        constructor name and its documentation URL slug. Prefer short entity
        names ("Wall", "Flip", "Create") over full sentences.

        Args:
            query: Entity name or member name to look up.
            year: Revit API year version (default from config, e.g. 2025).
            types: Filter by entity type: class, method, property, event,
                constructor, enum, interface, structure, delegate, field, operator.
            limit: Maximum number of results.

        Returns:
            JSON with matching entities including url slugs for get_api_doc.
        """
        if not deps.rvtdocs.available():
            return dumps({"query": query, "error": "rvtdocs backend is disabled"})
        try:
            hits = deps.rvtdocs.search(
                query,
                limit=max(1, min(limit, 50)),
                year=year,
                types=_normalize_types(types),
            )
        except RvtdocsError as exc:
            return dumps({"query": query, "error": str(exc)})

        return dumps(
            {
                "query": query,
                "year": year or deps.config.docs.year,
                "count": len(hits),
                "results": [
                    {
                        "title": hit.title,
                        "type": hit.kind,
                        "namespace": hit.metadata.get("namespace"),
                        "url": hit.url,
                        "slug": hit.metadata.get("slug"),
                    }
                    for hit in hits
                ],
            }
        )

    @mcp.tool()
    def get_api_doc(slugs: list[str], year: int | None = None) -> str:
        """Retrieve full Revit API documentation pages as markdown.

        Use after lookup_api or search_knowledge to read the authoritative page
        content (description, remarks, inheritance hierarchy, syntax, examples
        and member tables). Pass one or many slugs.

        Args:
            slugs: Documentation slugs or URLs, e.g. "Autodesk.Revit.DB.Wall",
                "/2025/Autodesk.Revit.DB.Wall" or a full rvtdocs.com URL.
            year: Year used to qualify bare slugs (default from config).

        Returns:
            JSON with markdown content per slug plus any errors.
        """
        if not deps.rvtdocs.available():
            return dumps({"error": "rvtdocs backend is disabled"})
        if not slugs:
            return dumps({"error": "provide at least one slug"})

        resolved_year = year or deps.config.docs.year
        docs = []
        errors = []
        for raw_slug in slugs:
            slug = raw_slug.strip()
            if not slug:
                continue
            if not slug.startswith(("http://", "https://", "/")):
                slug = f"/{resolved_year}/{slug.lstrip('/')}"
            try:
                markdown = deps.rvtdocs.fetch_markdown(slug)
            except RvtdocsError as exc:
                errors.append(f"{slug}: {exc}")
                continue
            docs.append(
                {
                    "slug": slug,
                    "url": page_url(deps.config.docs.base_url, slug),
                    "markdown": markdown,
                }
            )

        return dumps({"count": len(docs), "docs": docs, "errors": errors})
