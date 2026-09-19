from types import SimpleNamespace

from revit_knowledge_mcp.backends.qdrant_backend import payload_to_hit


def point(payload, score=0.5, point_id="1"):
    return SimpleNamespace(payload=payload, score=score, id=point_id)


def test_uuid_title_replaced_by_summary():
    hit = payload_to_hit(
        "Revit_SDK_Samples",
        point({"db_id": "4e088826-efdb-412f-bb14-551184510ac4", "summary": "Creates a wall in a project. More text."}),
    )
    assert hit.title == "Creates a wall in a project."
    assert hit.snippet.startswith("Creates a wall")


def test_name_prefix_becomes_kind():
    hit = payload_to_hit(
        "revit_api_knowledge",
        point({"name": "Overload:Autodesk.Revit.DB.Wall.Create", "summary": "Creates a wall."}),
    )
    assert hit.title == "Autodesk.Revit.DB.Wall.Create"
    assert hit.kind == "Overload"


def test_revitapidocs_href_becomes_url():
    hit = payload_to_hit(
        "revit_api",
        point({"title": "TransactionMode Enumeration", "text": "...", "href": "abc.htm", "version": "2022"}),
    )
    assert hit.url == "https://www.revitapidocs.com/2022/abc.htm"
