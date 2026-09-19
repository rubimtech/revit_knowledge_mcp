"""Shared runtime dependencies passed to tool registrars."""

from dataclasses import dataclass

from .backends import OpenAIBackend, QdrantBackend, RvtdocsBackend
from .config import AppConfig
from .embeddings import Embedder
from .registry import Registry


@dataclass
class Deps:
    config: AppConfig
    registry: Registry
    embedder: Embedder
    qdrant: QdrantBackend
    rvtdocs: RvtdocsBackend
    openai: OpenAIBackend
