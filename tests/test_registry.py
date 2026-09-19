from revit_knowledge_mcp.config import CollectionConfig
from revit_knowledge_mcp.registry import Registry


def make_registry() -> Registry:
    return Registry(
        [
            CollectionConfig(name="revit_api_knowledge", platform="revit"),
            CollectionConfig(name="navisworks_api_bge", platform="navisworks"),
            CollectionConfig(name="hidden", platform="revit", default=False),
        ]
    )


def test_default_names_exclude_disabled():
    registry = make_registry()
    assert registry.default_names() == ["revit_api_knowledge", "navisworks_api_bge"]


def test_resolve_by_platform():
    registry = make_registry()
    names, unknown = registry.resolve(platform="navisworks")
    assert names == ["navisworks_api_bge"]
    assert unknown == []


def test_resolve_explicit_keeps_unknown():
    registry = make_registry()
    names, unknown = registry.resolve(collections=["revit_api_knowledge", "mystery"])
    assert names == ["revit_api_knowledge", "mystery"]
    assert unknown == ["mystery"]


def test_resolve_explicit_and_platform_filters():
    registry = make_registry()
    names, _ = registry.resolve(
        collections=["revit_api_knowledge", "navisworks_api_bge"], platform="revit"
    )
    assert names == ["revit_api_knowledge"]


def test_platforms():
    assert make_registry().platforms() == ["revit", "navisworks"]
