"""Configuration loading for the unified knowledge MCP server.

Configuration precedence (lowest to highest):
1. built-in defaults
2. config.yaml (path from RKM_CONFIG, or <repo>/config.yaml)
3. environment variables

Secrets should be provided through the environment.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

DEFAULT_COLLECTIONS = [
    ("revit_api_knowledge", "revit", "Revit API documentation (CHM-derived)", True),
    ("Revit_SDK_Samples", "revit", "Revit SDK C# samples", True),
    ("pyRevit_Projects_Nice3point", "revit", "Python/pyRevit code samples", True),
    ("revit_api", "revit", "Revit API pages (jsonl)", True),
    ("navisworks_api_bge", "navisworks", "Navisworks API documentation", True),
    ("archicad_api_29", "archicad", "Archicad API 29 documentation", True),
    ("fsnb_bge", "other", "FSNB collection", False),
]

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent


class QdrantLocal(BaseModel):
    host: str = "127.0.0.1"
    port: int = 6333


class QdrantRemote(BaseModel):
    url: str = ""
    api_key: str = ""


class QdrantConfig(BaseModel):
    mode: str = "local"
    local: QdrantLocal = QdrantLocal()
    remote: QdrantRemote = QdrantRemote()


class EmbedLocal(BaseModel):
    ollama_url: str = "http://localhost:11434/api/embeddings"


class EmbedCloud(BaseModel):
    api_url: str = "https://polza.ai/api/v1"
    api_key: str = ""
    model: str = ""


class EmbedConfig(BaseModel):
    mode: str = "local"
    model: str = "bge-m3"
    local: EmbedLocal = EmbedLocal()
    cloud: EmbedCloud = EmbedCloud()


class DocsConfig(BaseModel):
    enabled: bool = True
    year: int = 2025
    base_url: str = "https://rvtdocs.com"
    search_url: str = "https://rvtdocs.com/search/v2/api/"


class OpenAIConfig(BaseModel):
    enabled: bool = True
    api_key: str = ""
    vector_store_id: str = ""


class CollectionConfig(BaseModel):
    name: str
    platform: str = "revit"
    description: str = ""
    embed_model: str = "bge-m3"
    default: bool = True


class AppConfig(BaseModel):
    qdrant: QdrantConfig = QdrantConfig()
    embed: EmbedConfig = EmbedConfig()
    docs: DocsConfig = DocsConfig()
    openai: OpenAIConfig = OpenAIConfig()
    collections: list[CollectionConfig] = []
    log_level: str = "INFO"

    def resolve_config_path(self) -> Path | None:
        env_path = os.environ.get("RKM_CONFIG")
        if env_path:
            return Path(env_path).expanduser()
        candidate = REPO_ROOT / "config.yaml"
        return candidate if candidate.exists() else None


def _load_yaml(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _apply_env(config: AppConfig) -> AppConfig:
    mode = _env("RKM_QDRANT_MODE")
    if mode:
        config.qdrant.mode = mode
    host = _env("RKM_QDRANT_HOST")
    if host:
        config.qdrant.local.host = host
    port = _env("RKM_QDRANT_PORT")
    if port:
        config.qdrant.local.port = int(port)
    url = _env("RKM_QDRANT_URL")
    if url:
        config.qdrant.mode = "remote"
        config.qdrant.remote.url = url
    api_key = _env("RKM_QDRANT_API_KEY")
    if api_key:
        config.qdrant.remote.api_key = api_key

    embed_mode = _env("RKM_EMBED_MODE")
    if embed_mode:
        config.embed.mode = embed_mode
    embed_model = _env("RKM_EMBED_MODEL")
    if embed_model:
        config.embed.model = embed_model
    ollama_url = _env("RKM_OLLAMA_URL")
    if ollama_url:
        config.embed.local.ollama_url = ollama_url
    embed_api_url = _env("RKM_EMBED_API_URL")
    if embed_api_url:
        config.embed.cloud.api_url = embed_api_url
    embed_api_key = _env("RKM_EMBED_API_KEY") or _env("POLZA_API_KEY")
    if embed_api_key:
        config.embed.cloud.api_key = embed_api_key
    cloud_model = _env("RKM_EMBED_CLOUD_MODEL")
    if cloud_model:
        config.embed.cloud.model = cloud_model

    docs_year = _env("RKM_DOCS_YEAR")
    if docs_year:
        config.docs.year = int(docs_year)
    docs_enabled = _env("RKM_DOCS_ENABLED")
    if docs_enabled is not None:
        config.docs.enabled = docs_enabled.lower() in {"1", "true", "yes", "on"}

    openai_key = _env("OPENAI_API_KEY") or _env("RKM_OPENAI_API_KEY")
    if openai_key:
        config.openai.api_key = openai_key
    vector_store = _env("OPENAI_VECTOR_STORE_ID") or _env("RKM_OPENAI_VECTOR_STORE_ID")
    if vector_store:
        config.openai.vector_store_id = vector_store

    log_level = _env("RKM_LOG_LEVEL")
    if log_level:
        config.log_level = log_level

    return config


def _default_collections() -> list[CollectionConfig]:
    return [
        CollectionConfig(name=name, platform=platform, description=description, default=is_default)
        for name, platform, description, is_default in DEFAULT_COLLECTIONS
    ]


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration from defaults, YAML and environment."""
    config = AppConfig()
    resolved = path or config.resolve_config_path()
    raw = _load_yaml(resolved)

    if raw:
        config = AppConfig.model_validate(raw)
    if not config.collections:
        config.collections = _default_collections()

    return _apply_env(config)
