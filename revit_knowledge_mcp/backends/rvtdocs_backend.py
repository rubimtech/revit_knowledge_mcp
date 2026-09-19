"""Live Revit API documentation backend (rvtdocs.com)."""

import logging
from typing import Any

from ..config import DocsConfig
from ..sources.html_to_md import page_to_markdown
from ..sources.rvtdocs import RvtdocsError, fetch_page, page_url, search_entities
from .base import SearchHit

log = logging.getLogger(__name__)


class RvtdocsBackend:
    """Entity lookup and documentation retrieval against rvtdocs.com."""

    id = "rvtdocs"

    def __init__(self, config: DocsConfig) -> None:
        self._config = config

    def available(self) -> bool:
        return self._config.enabled

    def search(
        self,
        query: str,
        limit: int = 10,
        year: int | None = None,
        types: list[str] | None = None,
        **kwargs: Any,
    ) -> list[SearchHit]:
        results = search_entities(
            self._config.search_url,
            query,
            year=year or self._config.year,
            types=types,
            limit=limit,
        )
        return [self._to_hit(result) for result in results]

    def fetch_markdown(self, slug: str) -> str:
        html = fetch_page(self._config.base_url, slug)
        return page_to_markdown(html)

    def _to_hit(self, result: dict[str, Any]) -> SearchHit:
        slug = result.get("url") or ""
        return SearchHit(
            source="rvtdocs",
            doc_id=str(result.get("page_id") or slug),
            title=result.get("title") or result.get("headline_main") or "",
            kind=result.get("type") or "",
            snippet=result.get("description") or "",
            url=page_url(self._config.base_url, slug) if slug else None,
            metadata={
                "page_id": result.get("page_id"),
                "year_version": result.get("year_version"),
                "namespace": result.get("namespace"),
                "declaring_type": result.get("declaring_type"),
                "is_obsolete": result.get("is_obsolete"),
                "slug": slug,
            },
        )


__all__ = ["RvtdocsBackend", "RvtdocsError"]
