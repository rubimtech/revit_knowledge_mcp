from revit_knowledge_mcp.backends.base import SearchHit
from revit_knowledge_mcp.ranking import fuse


def hit(doc_id: str, source: str = "qdrant", title: str = "t") -> SearchHit:
    return SearchHit(source=source, title=title, doc_id=doc_id)


def test_fuse_promotes_items_in_multiple_lists():
    list_a = [hit("a"), hit("b"), hit("c")]
    list_b = [hit("b"), hit("d")]
    result = fuse([list_a, list_b])
    assert result[0].doc_id == "b"
    assert result[0].rrf is not None


def test_fuse_keeps_distinct_items():
    result = fuse([[hit("a")], [hit("b")]])
    assert {h.doc_id for h in result} == {"a", "b"}


def test_fuse_assigns_rrf_scores():
    result = fuse([[hit("a"), hit("b")]])
    assert result[0].rrf > result[1].rrf
