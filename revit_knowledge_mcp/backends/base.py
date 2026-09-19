"""Shared backend types."""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class SearchHit:
    """A normalized search result from any backend."""

    source: str
    title: str
    snippet: str = ""
    url: str | None = None
    collection: str | None = None
    doc_id: str | None = None
    score: float | None = None
    kind: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    rrf: float | None = None

    def key(self) -> str:
        parts = [self.source, self.collection or "", self.doc_id or self.url or self.title]
        return ":".join(parts)

    def to_dict(self, snippet_limit: int = 500) -> dict[str, Any]:
        snippet = self.snippet or ""
        if snippet_limit and len(snippet) > snippet_limit:
            snippet = snippet[:snippet_limit].rstrip() + "…"
        return {
            "source": self.source,
            "collection": self.collection,
            "title": self.title,
            "kind": self.kind,
            "url": self.url,
            "score": self.score,
            "rrf": self.rrf,
            "snippet": snippet,
            "metadata": self.metadata,
        }


@runtime_checkable
class SearchBackend(Protocol):
    """A source of ranked search hits."""

    id: str

    def available(self) -> bool:
        ...

    def search(self, query: str, limit: int, **kwargs: Any) -> list[SearchHit]:
        ...
