"""Unified Revit knowledge MCP server (stdio)."""

import logging
import sys

from mcp.server import FastMCP

from .backends import OpenAIBackend, QdrantBackend, RvtdocsBackend
from .config import AppConfig, load_config
from .deps import Deps
from .embeddings import Embedder
from .registry import Registry
from .tools.api_docs import register_api_docs_tools
from .tools.collections import register_collection_tools
from .tools.knowledge import register_knowledge_tools
from .tools.research import register_research_tools

log = logging.getLogger(__name__)

INSTRUCTIONS = """\
Unified Revit/Archicad/Navisworks knowledge server.

Two complementary tiers:

1. Semantic knowledge (search_knowledge, research): pre-embedded Qdrant
   collections with bge-m3 covering Revit API docs, SDK samples, pyRevit code,
   Navisworks and Archicad API documentation. Use natural language.
2. Live official documentation (lookup_api, get_api_doc): the rvtdocs.com
   index and full markdown pages. Use exact entity names to confirm the real
   API surface and avoid hallucination.

Use `research` to combine both in one call. Use `list_collections` to see what
knowledge is available.
"""


def build_deps(config: AppConfig | None = None) -> Deps:
    config = config or load_config()
    registry = Registry(config.collections)
    embedder = Embedder(config.embed)
    return Deps(
        config=config,
        registry=registry,
        embedder=embedder,
        qdrant=QdrantBackend(config.qdrant, embedder, registry),
        rvtdocs=RvtdocsBackend(config.docs),
        openai=OpenAIBackend(config.openai),
    )


def build_server(deps: Deps | None = None, config: AppConfig | None = None) -> FastMCP:
    deps = deps or build_deps(config)
    mcp = FastMCP(
        "revit-knowledge",
        instructions=INSTRUCTIONS,
        log_level=deps.config.log_level.upper(),
    )
    register_knowledge_tools(mcp, deps)
    register_api_docs_tools(mcp, deps)
    register_collection_tools(mcp, deps)
    register_research_tools(mcp, deps)
    return mcp


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        stream=sys.stderr,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Keep third-party HTTP clients quiet: stdio servers must stay lean, and
    # qdrant_client logs every request at INFO.
    for noisy in ("httpx", "httpcore", "urllib3", "qdrant_client"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main() -> None:
    config = load_config()
    _configure_logging(config.log_level)

    deps = build_deps(config)
    qdrant_available = deps.qdrant.available()
    log.info(
        "starting revit-knowledge MCP | qdrant=%s (%s) | embed=%s/%s | docs=%s | openai=%s",
        qdrant_available,
        config.qdrant.mode,
        config.embed.mode,
        deps.embedder.model,
        deps.rvtdocs.available(),
        deps.openai.available(),
    )
    if not qdrant_available:
        log.warning(
            "Qdrant is not reachable; semantic search will report errors until it is up"
        )

    build_server(deps).run()


if __name__ == "__main__":
    main()
