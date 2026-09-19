"""Embedding providers.

The Qdrant collections were indexed with ``bge-m3`` (1024 dimensions). Query
embeddings must use the same model/dimension, so the model is configured per
collection in the catalog and defaults to ``embed.model``.
"""

import logging

import requests

from .config import EmbedConfig

log = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Raised when an embedding provider cannot produce a vector."""


class Embedder:
    """Produces query embeddings via Ollama (local) or an OpenAI-compatible API."""

    def __init__(self, config: EmbedConfig) -> None:
        self._config = config
        self._cache: dict[str, list[float]] = {}

    @property
    def model(self) -> str:
        if self._config.mode == "cloud":
            return self._config.cloud.model or self._config.model
        return self._config.model

    def embed(self, text: str, model: str | None = None) -> list[float]:
        text = text.strip()
        if not text:
            raise EmbeddingError("Cannot embed an empty query")
        model = model or self.model
        cache_key = f"{self._config.mode}:{model}:{text}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        vector = (
            self._embed_local(text, model)
            if self._config.mode == "local"
            else self._embed_cloud(text, model)
        )
        self._cache[cache_key] = vector
        return vector

    def _embed_local(self, text: str, model: str) -> list[float]:
        url = self._config.local.ollama_url
        try:
            response = requests.post(
                url,
                json={"model": model, "prompt": text},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise EmbeddingError(f"Ollama request failed at {url}: {exc}") from exc
        except ValueError as exc:
            raise EmbeddingError(f"Ollama returned invalid JSON at {url}: {exc}") from exc

        vector = payload.get("embedding")
        if not vector and "embeddings" in payload:
            embeddings = payload["embeddings"]
            vector = embeddings[0] if embeddings else None
        if not vector:
            raise EmbeddingError(
                f"Ollama response from {url} did not contain an embedding"
            )
        return list(vector)

    def _embed_cloud(self, text: str, model: str) -> list[float]:
        url = self._cloud_endpoint()
        api_key = self._config.cloud.api_key
        if not api_key:
            raise EmbeddingError(
                "Cloud embedding selected but no API key is configured "
                "(set RKM_EMBED_API_KEY or POLZA_API_KEY)"
            )
        try:
            response = requests.post(
                url,
                json={"input": text, "model": model},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise EmbeddingError(f"Embedding API request failed at {url}: {exc}") from exc
        except ValueError as exc:
            raise EmbeddingError(f"Embedding API returned invalid JSON at {url}: {exc}") from exc

        data = payload.get("data") or []
        if not data or "embedding" not in data[0]:
            raise EmbeddingError(
                f"Embedding API response from {url} did not contain data[0].embedding"
            )
        return list(data[0]["embedding"])

    def _cloud_endpoint(self) -> str:
        base = self._config.cloud.api_url.rstrip("/")
        if base.endswith("/embeddings"):
            return base
        return f"{base}/embeddings"
