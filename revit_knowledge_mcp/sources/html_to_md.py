"""Convert rvtdocs.com documentation HTML into markdown.

The upstream site was redesigned, so this parser is structure-based (classes
and headings) rather than relying on the specific HTML comments the old
Rvt_Docs_MCP parser used. A generic fallback handles pages whose layout does
not match the expected cards.
"""

import re

from bs4 import BeautifulSoup, Tag

LANG_MAP = {
    "cs": "csharp",
    "csharp": "csharp",
    "vb": "vbnet",
    "vbnet": "vbnet",
    "cpp": "cpp",
    "c": "cpp",
    "fs": "fsharp",
    "fsharp": "fsharp",
    "python": "python",
    "py": "python",
}

# rvtdocs marks every syntax block as language-cs even for VB/C++/F#, so the
# language is taken from the tab label instead.
TAB_LANG = {
    "c#": "csharp",
    "csharp": "csharp",
    "vb": "vbnet",
    "vbnet": "vbnet",
    "c++": "cpp",
    "cpp": "cpp",
    "f#": "fsharp",
    "fsharp": "fsharp",
    "python": "python",
    "py": "python",
}

SKIP_SECTION_MARKERS = ("community snippet", "discussion", "comment")
CELL_LIMIT = 400


def page_to_markdown(html: str) -> str:
    """Extract the main documentation content from a page as markdown."""
    soup = BeautifulSoup(html, "html.parser")
    _remove_noise(soup)

    parts: list[str] = []
    header = _render_header(soup)
    if header:
        parts.append(header)

    seen_cards: set[int] = set()
    for label, card in _iter_sections(soup):
        if id(card) in seen_cards:
            continue
        seen_cards.add(id(card))
        rendered = _render_section(label, card)
        if rendered:
            parts.append(rendered)

    if len(parts) <= 1:
        fallback = _generic_markdown(soup)
        if fallback:
            parts.append(fallback)

    markdown = "\n\n".join(part for part in parts if part.strip())
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def _remove_noise(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    for selector in ("nav", "header", "footer", "aside", ".rvt-toc", ".sidebar", ".navbar", ".breadcrumb"):
        for tag in soup.select(selector):
            tag.decompose()


def _clean(text: str) -> str:
    return " ".join(text.split())


def _text_with_breaks(tag: Tag) -> str:
    for br in tag.find_all("br"):
        br.replace_with("\n")
    text = tag.get_text("", strip=False)
    lines = [_clean(line) for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def _find_namespace(soup: BeautifulSoup) -> str:
    """Return the namespace only from an explicit, trustworthy element.

    Fallback selectors must stay narrow: generic ``[class*=namespace]`` matches
    member-table wrappers (``namespace-table-body``) and would leak table text.
    """
    for element in soup.select(".card-namespace, [class*=namespace-label]"):
        match = re.match(r"^Namespace:\s*(.+)$", _clean(element.get_text(" ", strip=True)))
        if match:
            return match.group(1).strip()
    node = soup.find(string=re.compile(r"^\s*Namespace:"))
    if node is not None and node.parent is not None:
        match = re.match(r"^Namespace:\s*(.+)$", _clean(node.parent.get_text(" ", strip=True)))
        if match:
            return match.group(1).strip()
    return ""


def _render_header(soup: BeautifulSoup) -> str:
    title_tag = soup.select_one(".card-title h1") or soup.find("h1")
    title = _clean(title_tag.get_text(" ", strip=True)) if title_tag else ""

    lines: list[str] = []
    if title:
        lines.append(f"# {title}")

    icon = soup.select_one(".headline-type-icon")
    if icon is not None:
        kind = (icon.get("title") or _clean(icon.get_text(" ", strip=True)) or "").strip()
        if kind:
            lines.append(f"**Type:** {kind}")

    namespace = _find_namespace(soup)
    if namespace:
        lines.append(f"**Namespace:** {namespace}")

    description = soup.select_one(".card-description")
    if description is not None:
        text = _text_with_breaks(description)
        text = re.sub(r"^Description:\s*", "", text).strip()
        if text:
            lines.append(f"## Description\n\n{text}")

    remarks = soup.select_one(".card-remarks")
    if remarks is not None:
        text = _text_with_breaks(remarks)
        text = re.sub(r"^Remarks:\s*", "", text).strip()
        if text:
            lines.append(f"## Remarks\n\n{text}")

    hierarchy = soup.select_one(".card-hierarchy")
    if hierarchy is not None:
        text = _text_with_breaks(hierarchy)
        text = re.sub(r"^Inheritance Hierarchy:\s*", "", text).strip()
        if text:
            lines.append(f"## Hierarchy\n\n{text}")

    return "\n\n".join(lines)


def _iter_sections(soup: BeautifulSoup):
    for heading in soup.find_all("h2"):
        label = _clean(heading.get_text(" ", strip=True))
        if not label:
            continue
        card = heading.find_parent(
            class_=lambda value: bool(value)
            and any("card" in cls for cls in ([value] if isinstance(value, str) else value))
        )
        yield label, card or heading.parent


def _render_section(label: str, card: Tag) -> str:
    low = label.lower()
    if any(marker in low for marker in SKIP_SECTION_MARKERS):
        return ""

    if "syntax" in low:
        code = _render_code(card)
        return f"## {label}\n\n{code}" if code else ""

    if "example" in low:
        code = _render_code(card)
        return f"## {label}\n\n{code}" if code else ""

    table = card.find("table")
    if table is not None:
        rendered = _table_to_markdown(table)
        if rendered:
            return f"## {label}\n\n{rendered}"

    code = _render_code(card)
    if code:
        return f"## {label}\n\n{code}"

    text = _clean(card.get_text(" ", strip=True))
    if text and len(text) > 3:
        return f"## {label}\n\n{text}"
    return ""


def _language(code_element: Tag) -> str:
    for cls in code_element.get("class") or []:
        if cls.startswith("language-"):
            raw = cls[len("language-"):].lower()
            return LANG_MAP.get(raw, raw)
    return ""


def _tab_key(label: str) -> str:
    return re.sub(r"[^a-z0-9#+]", "", label.lower())


def _tab_labels(container: Tag) -> dict[str, str]:
    labels: dict[str, str] = {}
    for button in container.select(".tabs [data-tab-index], .example-tabs [data-tab-index]"):
        index = button.get("data-tab-index")
        if index is None:
            continue
        label = _clean(button.get_text(" ", strip=True))
        if label:
            labels[str(index)] = label
    return labels


def _render_code(container: Tag) -> str:
    tabs = _tab_labels(container)
    blocks: list[str] = []
    seen: set[tuple[str, str]] = set()

    snippets = container.select(".code-snippet") or container.find_all("pre")
    for snippet in snippets:
        code_element = snippet.find("code") or snippet
        code = code_element.get_text()
        if not code.strip():
            continue
        index = snippet.get("data-tab-index")
        label = tabs.get(str(index), "") if index is not None else ""
        language = TAB_LANG.get(_tab_key(label), "") or _language(code_element)
        key = (language, code)
        if key in seen:
            continue
        seen.add(key)
        blocks.append(f"```{language}\n{code.strip()}\n```")
    return "\n\n".join(blocks)


def _table_to_markdown(table: Tag) -> str:
    header_cells: list[str] = []
    thead = table.find("thead")
    if thead is not None:
        header_row = thead.find("tr")
        if header_row is not None:
            header_cells = [_cell_text(cell) for cell in header_row.find_all(["th", "td"])]

    body_rows: list[list[str]] = []
    tbody = table.find("tbody") or table
    for row in tbody.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        body_rows.append([_cell_text(cell) for cell in cells])

    if not header_cells and body_rows:
        header_cells = [f"col{i + 1}" for i in range(len(body_rows[0]))]
    if not header_cells:
        return ""

    width = len(header_cells)
    lines = ["| " + " | ".join(header_cells) + " |"]
    lines.append("|" + "|".join(["---"] * width) + "|")
    for row in body_rows:
        padded = (row + [""] * width)[:width]
        lines.append("| " + " | ".join(padded) + " |")
    return "\n".join(lines)


def _cell_text(cell: Tag) -> str:
    text = _clean(cell.get_text(" ", strip=True)).replace("|", "\\|")
    if len(text) > CELL_LIMIT:
        text = text[:CELL_LIMIT].rstrip() + "…"
    return text


def _generic_markdown(soup: BeautifulSoup) -> str:
    root = soup.select_one("main") or soup.select_one("#main-content") or soup.body
    if root is None:
        return ""
    lines: list[str] = []
    for element in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre", "table"]):
        name = element.name
        if name in ("h1", "h2", "h3", "h4"):
            text = _clean(element.get_text(" ", strip=True))
            if text:
                lines.append("#" * int(name[1]) + " " + text)
        elif name == "p":
            text = _clean(element.get_text(" ", strip=True))
            if text:
                lines.append(text)
        elif name == "li":
            text = _clean(element.get_text(" ", strip=True))
            if text:
                lines.append("- " + text)
        elif name == "pre":
            code = element.get_text().strip()
            if code:
                lines.append(f"```\n{code}\n```")
        elif name == "table":
            rendered = _table_to_markdown(element)
            if rendered:
                lines.append(rendered)
    return "\n\n".join(line for line in lines if line)
