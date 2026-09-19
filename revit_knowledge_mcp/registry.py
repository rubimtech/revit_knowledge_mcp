"""Catalog of knowledge collections and platform filtering."""

from .config import CollectionConfig


class Registry:
    """Known Qdrant collections and their metadata."""

    def __init__(self, collections: list[CollectionConfig]) -> None:
        self._collections = list(collections)

    def all(self) -> list[CollectionConfig]:
        return list(self._collections)

    def names(self) -> list[str]:
        return [c.name for c in self._collections]

    def default_names(self) -> list[str]:
        return [c.name for c in self._collections if c.default]

    def get(self, name: str) -> CollectionConfig | None:
        for collection in self._collections:
            if collection.name == name:
                return collection
        return None

    def platforms(self) -> list[str]:
        seen: list[str] = []
        for collection in self._collections:
            if collection.platform not in seen:
                seen.append(collection.platform)
        return seen

    def platform_names(self, platform: str) -> list[str]:
        return [c.name for c in self._collections if c.platform == platform]

    def resolve(
        self,
        collections: list[str] | None = None,
        platform: str | None = None,
    ) -> tuple[list[str], list[str]]:
        """Resolve requested collections.

        Returns ``(resolved_names, unknown_names)``. Unknown names are still
        returned as searchable so that collections absent from the catalog keep
        working; callers surface them separately.
        """
        if collections:
            resolved = list(collections)
            if platform:
                allowed = set(self.platform_names(platform))
                filtered = [name for name in resolved if name in allowed]
                if filtered:
                    resolved = filtered
            unknown = [name for name in resolved if self.get(name) is None]
            return resolved, unknown

        if platform:
            return self.platform_names(platform), []

        return self.default_names(), []
