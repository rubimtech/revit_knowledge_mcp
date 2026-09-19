import pytest

from revit_knowledge_mcp.backends.base import SearchHit
from revit_knowledge_mcp.sources.rvtdocs import RvtdocsError, fetch_page, page_url
from revit_knowledge_mcp.tools.research import _matches_entity

BASE = "https://rvtdocs.com"


def test_page_url_builds_absolute_from_slug():
    assert page_url(BASE, "/2025/Autodesk.Revit.DB.Wall") == "https://rvtdocs.com/2025/Autodesk.Revit.DB.Wall"
    assert page_url(BASE, "2025/Autodesk.Revit.DB.Wall") == "https://rvtdocs.com/2025/Autodesk.Revit.DB.Wall"


def test_fetch_page_rejects_foreign_host_without_network():
    with pytest.raises(RvtdocsError):
        fetch_page(BASE, "http://169.254.169.254/latest/meta-data/")
    with pytest.raises(RvtdocsError):
        fetch_page(BASE, "https://rvtdocs.com.evil.test/2025/Wall")


def test_matches_entity_accepts_relevant_hit():
    hit = SearchHit(source="rvtdocs", title="Wall.Flip Method")
    assert _matches_entity("Flip", hit) is True
    assert _matches_entity("Autodesk.Revit.DB.Wall.Flip", hit) is True


def test_matches_entity_rejects_unrelated_hit():
    hit = SearchHit(source="rvtdocs", title="Wall.Create Method")
    assert _matches_entity("Flip", hit) is False
