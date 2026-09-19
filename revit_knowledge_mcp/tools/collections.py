"""Collection introspection tools."""

import logging

from ..backends import QdrantUnavailable
from ..deps import Deps
from .common import dumps

log = logging.getLogger(__name__)


def register_collection_tools(mcp, deps: Deps) -> None:
    @mcp.tool()
    def list_collections() -> str:
        """List Qdrant knowledge collections with point counts.

        Internal workspace collections are hidden. Catalog collections are
        annotated with their platform and description.

        Returns:
            Plain text list of "name: N points [platform] description".
        """
        try:
            collections = deps.qdrant.list_collections()
        except QdrantUnavailable as exc:
            return f"Qdrant unavailable: {exc}"
        except Exception as exc:  # pragma: no cover - environment dependent
            return f"Qdrant unavailable: {exc}"

        lines = ["Qdrant collections:"]
        for name, count in sorted(collections, key=lambda item: item[0]):
            info = deps.registry.get(name)
            suffix = ""
            if info is not None:
                suffix = f" [{info.platform}] {info.description}".rstrip()
            lines.append(f"  {name}: {count} points{suffix}")
        return "\n".join(lines)

    @mcp.tool()
    def check_collection(collection: str) -> str:
        """Check that a Qdrant collection exists and return its point count.

        Args:
            collection: Collection name, e.g. "revit_api_knowledge".

        Returns:
            Plain text status message.
        """
        try:
            count = deps.qdrant.collection_count(collection)
        except Exception as exc:
            return f"Collection '{collection}' not accessible: {exc}"
        return f"Collection '{collection}': {count} points"
