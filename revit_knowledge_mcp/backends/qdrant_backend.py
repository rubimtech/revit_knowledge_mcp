"""Qdrant semantic search backend."""

import logging
import re
from typing import Any

from qdrant_client import QdrantClient

from ..config import QdrantConfig
from ..embeddings import Embedder, EmbeddingError
from ..registry import Registry
from .base import SearchHit

log = logging.getLogger(__name__)

TITLE_KEYS = ("title", "name", "source", "id", "db_id")
SNIPPET_KEYS = ("summary", "text", "description", "syntax", "params", "code")
EXTRA_SNIPPET_KEYS = ("syntax", "params", "code")
URL_KEYS = ("href", "url", "link")
KIND_KEYS = ("type", "doc_type", "tag")
REVITAPIDOCS_BASE = "https://www.revitapidocs.com"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _derive_title(snippet: str) -> str:
    """Build a readable title from a payload that only carries a summary."""
    if not snippet:
        return ""
    first = re.split(r"(?<=[.!?])\s|\n", snippet.strip(), maxsplit=1)[0].strip()
    if len(first) > 90:
        first = first[:90].rstrip() + "…"
    return first


class QdrantUnavailable(RuntimeError):
    """Raised when the Qdrant backend cannot be reached."""


def is_internal_collection(name: str) -> bool:
    """Internal workspace/test collections are hidden from listings."""
    return name.startswith("ws-") or name.startswith("_")


def _first(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value and not isinstance(value, str):
            return str(value)
    return ""


def payload_to_hit(collection: str, point: Any) -> SearchHit:
    """Normalize a heterogeneous Qdrant payload into a SearchHit."""
    payload = dict(point.payload or {})
    title = _first(payload, TITLE_KEYS)
    kind = _first(payload, KIND_KEYS)

    name = payload.get("name")
    if isinstance(name, str) and ":" in name:
        prefix, _, rest = name.partition(":")
        title = rest.strip() or title
        kind = kind or prefix.split(".")[0]

    snippet = _first(payload, SNIPPET_KEYS)
    if not snippet:
        snippet = _first(payload, EXTRA_SNIPPET_KEYS)
    else:
        extras = _first(payload, EXTRA_SNIPPET_KEYS)
        if extras and extras not in snippet:
            snippet = f"{snippet}\n\n{extras}"

    if not title:
        source = str(payload.get("source") or payload.get("db_id") or "")
        title = source.rsplit("/", 1)[-1] if source else f"{collection} result"

    # Collections holding code samples often expose only a db_id plus a
    # summary; a UUID is not a useful title.
    if UUID_RE.match(title):
        title = _derive_title(snippet) or f"{collection} {title[:8]}"

    url = _first(payload, URL_KEYS) or None
    if url and not url.startswith("http"):
        version = payload.get("version") or ""
        if url.endswith(".htm") and version:
            url = f"{REVITAPIDOCS_BASE}/{version}/{url}"
        else:
            url = None

    return SearchHit(
        source="qdrant",
        collection=collection,
        doc_id=str(point.id),
        title=title,
        kind=kind,
        snippet=snippet,
        url=url,
        score=round(float(point.score), 4) if point.score is not None else None,
        metadata=_serializable(payload),
    )


def _serializable(payload: dict[str, Any]) -> dict[str, Any]:
    """Best-effort conversion of payload values for JSON output."""
    result: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
        elif isinstance(value, (list, dict)):
            result[key] = value
        else:
            result[key] = str(value)
    return result


class QdrantBackend:
    """Semantic search across Qdrant collections."""

    id = "qdrant"

    def __init__(self, config: QdrantConfig, embedder: Embedder, registry: Registry) -> None:
        self._config = config
        self._embedder = embedder
        self._registry = registry
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            try:
                if self._config.mode == "remote":
                    url = self._config.remote.url
                    if not url:
                        raise QdrantUnavailable("qdrant.mode is 'remote' but no URL is configured")
                    self._client = QdrantClient(
                        url=url,
                        api_key=self._config.remote.api_key or None,
                        timeout=30,
                    )
                else:
                    self._client = QdrantClient(
                        host=self._config.local.host,
                        port=self._config.local.port,
                        timeout=30,
                    )
            except QdrantUnavailable:
                raise
            except Exception as exc:  # pragma: no cover - depends on environment
                raise QdrantUnavailable(f"cannot create Qdrant client: {exc}") from exc
        return self._client

    def available(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def search(
        self,
        query: str,
        limit: int = 5,
        collections: list[str] | None = None,
        platform: str | None = None,
        **kwargs: Any,
    ) -> list[SearchHit]:
        grouped, _ = self.search_grouped(query, limit=limit, collections=collections, platform=platform)
        hits = [hit for group in grouped.values() for hit in group]
        hits.sort(key=lambda hit: hit.score or 0.0, reverse=True)
        return hits

    def search_grouped(
        self,
        query: str,
        limit: int = 5,
        collections: list[str] | None = None,
        platform: str | None = None,
    ) -> tuple[dict[str, list[SearchHit]], list[str]]:
        names, _ = self._registry.resolve(collections, platform)
        if not names:
            return {}, ["no collections selected"]

        try:
            vector = self._embedder.embed(query)
        except EmbeddingError as exc:
            raise QdrantUnavailable(str(exc)) from exc

        grouped: dict[str, list[SearchHit]] = {}
        errors: list[str] = []
        for name in names:
            try:
                points = self.client.query_points(
                    collection_name=name,
                    query=vector,
                    limit=max(1, min(limit, 50)),
                    with_payload=True,
                ).points
            except Exception as exc:
                log.warning("qdrant search failed for %s: %s", name, exc)
                errors.append(f"{name}: {exc}")
                continue
            if points:
                grouped[name] = [payload_to_hit(name, point) for point in points]
        return grouped, errors

    def list_collections(self, include_internal: bool = False) -> list[tuple[str, int]]:
        info = self.client.get_collections()
        collections: list[tuple[str, int]] = []
        for collection in info.collections:
            if not include_internal and is_internal_collection(collection.name):
                continue
            try:
                count = self.client.count(collection.name, exact=False).count
            except Exception:
                count = -1
            collections.append((collection.name, count))
        return collections

    def collection_count(self, name: str) -> int:
        return self.client.count(name, exact=False).count
