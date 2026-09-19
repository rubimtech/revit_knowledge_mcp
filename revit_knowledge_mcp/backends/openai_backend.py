"""Optional OpenAI vector store backend.

Uses the REST endpoint directly so the server does not depend on the OpenAI
Python SDK:

    POST https://api.openai.com/v1/vector_stores/{id}/search
"""

import logging
from typing import Any

import requests

from ..config import OpenAIConfig
from .base import SearchHit

log = logging.getLogger(__name__)

API_BASE = "https://api.openai.com/v1"


class OpenAIBackend:
    """Semantic search over an OpenAI vector store (The Building Coder etc.)."""

    id = "openai"

    def __init__(self, config: OpenAIConfig) -> None:
        self._config = config

    def available(self) -> bool:
        return bool(
            self._config.enabled
            and self._config.api_key
            and self._config.vector_store_id
        )

    def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.0,
        rewrite_query: bool = True,
        **kwargs: Any,
    ) -> list[SearchHit]:
        if not self.available():
            return []

        url = f"{API_BASE}/vector_stores/{self._config.vector_store_id}/search"
        body: dict[str, Any] = {
            "query": query,
            "max_num_results": max(1, min(limit, 50)),
            "rewrite_query": rewrite_query,
        }
        if score_threshold:
            body["ranking_options"] = {
                "ranker": "auto",
                "score_threshold": score_threshold,
            }

        response = requests.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return [self._to_hit(item) for item in payload.get("data") or []]

    def _to_hit(self, item: dict[str, Any]) -> SearchHit:
        content = item.get("content") or []
        snippet = "\n\n".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        ).strip()
        return SearchHit(
            source="openai",
            doc_id=item.get("file_id") or item.get("id"),
            title=item.get("filename") or item.get("file_id") or "vector store result",
            kind="vector_store",
            snippet=snippet,
            score=round(float(item["score"]), 4) if item.get("score") is not None else None,
            metadata={"attributes": item.get("attributes"), "file_id": item.get("file_id")},
        )
