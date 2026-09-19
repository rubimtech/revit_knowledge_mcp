"""Client for the rvtdocs.com search and documentation pages.

rvtdocs.com was redesigned after Rvt_Docs_MCP was written: the old
``/search/api/search`` endpoint now returns 404 and the DB-backed search lives
at ``/search/v2/api/`` (GET). The ``fields`` query parameter is required, and
passing no fields yields zero results.
"""

import logging
from typing import Any
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; revit-knowledge-mcp/0.1)"
SEARCH_FIELDS = "name,description"
BROADER_FIELDS = "title,parameters,description,syntax,inheritance,remarks"


class RvtdocsError(RuntimeError):
    """Raised when rvtdocs.com cannot be reached or returns an error."""


def page_url(base_url: str, slug: str) -> str:
    """Build an absolute documentation URL from a slug or URL."""
    if slug.startswith("http://") or slug.startswith("https://"):
        return slug
    base = base_url.rstrip("/")
    return f"{base}/{slug.lstrip('/')}"


def search_entities(
    search_url: str,
    query: str,
    year: int | None = None,
    types: list[str] | None = None,
    limit: int = 10,
    fields: str = SEARCH_FIELDS,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Search rvtdocs entities (classes, methods, properties, ...)."""
    params: dict[str, Any] = {
        "q": query,
        "fields": fields,
        "limit": str(max(1, min(limit, 50))),
        "source": "popup",
    }
    if year:
        params["v"] = str(year)
    if types:
        params["types"] = ",".join(types)

    try:
        response = requests.get(
            search_url,
            params=params,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RvtdocsError(f"rvtdocs search failed: {exc}") from exc
    except ValueError as exc:
        raise RvtdocsError(f"rvtdocs search returned invalid JSON: {exc}") from exc

    results = payload.get("results") or []

    # A zero-result exact query often means the search backend needs broader
    # fields; retry once before giving up.
    if not results and fields != BROADER_FIELDS:
        return search_entities(
            search_url,
            query,
            year=year,
            types=types,
            limit=limit,
            fields=BROADER_FIELDS,
            timeout=timeout,
        )
    return results


def fetch_page(base_url: str, slug: str, timeout: int = 30) -> str:
    """Fetch a documentation page's HTML.

    Only URLs on the configured documentation host are fetched. This prevents
    ``get_api_doc`` from being used as an SSRF vector when it is handed an
    arbitrary URL by untrusted content.
    """
    url = page_url(base_url, slug)
    parsed = urlparse(url)
    base_host = urlparse(base_url).netloc.lower()
    if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != base_host:
        raise RvtdocsError(
            f"refusing to fetch {url!r}: only {base_host} URLs are allowed"
        )
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RvtdocsError(f"failed to fetch {url}: {exc}") from exc
    return response.text
