from revit_knowledge_mcp.sources.html_to_md import page_to_markdown

SAMPLE = """
<html><body>
<header>site header noise</header>
<main>
  <div class="card-title flex">
    <span class="headline-type-icon is-class" title="Class">C</span>
    <h1>Wall</h1>
  </div>
  <div class="card-description"><strong>Description:</strong><br> Represents a wall.</div>
  <div class="card-remarks"><strong>Remarks:</strong><br> Wall remarks.</div>
  <div class="card-hierarchy"><strong>Inheritance Hierarchy:</strong><br><a>System.Object</a><br>Wall</div>
  <div class="card w-full">
    <h2 class="card-toolbar-h"><span class="card-toolbar-label">Syntax</span></h2>
    <div class="tabs mb-2">
      <button class="tab tab-active" data-tab-index="0">C#</button>
      <button class="tab" data-tab-index="1">VB</button>
    </div>
    <div class="code-snippets">
      <div class="code-snippet" data-tab-index="0"><pre><code class="hljs language-cs">public class Wall : HostObject</code></pre></div>
      <div class="code-snippet" data-tab-index="1"><pre><code class="hljs language-cs">Public Class Wall</code></pre></div>
    </div>
  </div>
  <div class="card member-section-card">
    <h2 class="card-toolbar-h"><span class="card-toolbar-label">Methods
      <span class="member-section-count">(2 members)</span></span></h2>
    <div class="member-section-body">
      <table>
        <thead><tr><th>Name</th><th>Description</th></tr></thead>
        <tbody><tr><td>Flip()</td><td>Flips the wall.</td></tr></tbody>
      </table>
    </div>
  </div>
  <div class="card">
    <h2 class="card-toolbar-h"><span class="card-toolbar-label">Community Snippets</span></h2>
    <p>ignore me</p>
  </div>
</main>
<footer>footer noise</footer>
</body></html>
"""


def test_header_and_members():
    markdown = page_to_markdown(SAMPLE)
    assert "# Wall" in markdown
    assert "**Type:** Class" in markdown
    assert "Represents a wall." in markdown
    assert "Wall remarks." in markdown
    assert "## Hierarchy" in markdown
    assert "System.Object" in markdown


def test_code_sections():
    markdown = page_to_markdown(SAMPLE)
    assert "## Syntax" in markdown
    assert "```csharp" in markdown
    assert "public class Wall : HostObject" in markdown
    assert "```vbnet" in markdown


def test_member_table_and_skips():
    markdown = page_to_markdown(SAMPLE)
    assert "## Methods (2 members)" in markdown
    assert "| Name | Description |" in markdown
    assert "| Flip() | Flips the wall. |" in markdown
    assert "Community Snippets" not in markdown


def test_generic_fallback():
    html = "<html><body><main><h1>Foo</h1><p>Bar baz</p><pre>some code</pre></main></body></html>"
    markdown = page_to_markdown(html)
    assert "# Foo" in markdown
    assert "Bar baz" in markdown
    assert "some code" in markdown


def test_namespace_not_leaked_from_member_table():
    html = """
    <html><body><main>
      <div class="card-title"><h1>Wall</h1></div>
      <div class="namespace-table-body">M Flip () Flips the wall.</div>
    </main></body></html>
    """
    markdown = page_to_markdown(html)
    assert "**Namespace:**" not in markdown


def test_namespace_from_explicit_element():
    html = """
    <html><body><main>
      <div class="card-title"><h1>Wall</h1></div>
      <div class="card-namespace">Namespace: Autodesk.Revit.DB</div>
    </main></body></html>
    """
    markdown = page_to_markdown(html)
    assert "**Namespace:** Autodesk.Revit.DB" in markdown
