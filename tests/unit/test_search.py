from __future__ import annotations

from pathlib import Path

from devdoc.search import DocumentIndex, _extract_title, build_index


def test_document_index_prefers_title_matches():
    index = DocumentIndex()
    index.add_document(
        "python/reference.md",
        "asyncio gather waits for tasks and returns results",
        "python",
        title="Asyncio Gather Reference",
    )
    index.add_document(
        "python/overview.md",
        "gather can also appear in a generic overview page",
        "python",
        title="Overview",
    )

    results = index.search("gather")

    assert [result["path"] for result in results] == [
        "python/reference.md",
        "python/overview.md",
    ]


def test_build_index_includes_markdown_and_rst_files(tmp_path: Path):
    source_dir = tmp_path / "python"
    source_dir.mkdir()
    (source_dir / "guide.md").write_text(
        "# Getting Started\n\nhello markdown", encoding="utf-8"
    )
    (source_dir / "notes.rst").write_text("title: Notes\n\nhello rst", encoding="utf-8")

    index = build_index({"python": {"path": str(source_dir)}})

    assert index.document_count == 2
    results = index.search("hello")
    assert {result["path"] for result in results} == {
        "python/guide.md",
        "python/notes.rst",
    }


def test_extract_title_uses_fallback_when_no_frontmatter_or_heading():
    assert (
        _extract_title("plain text only", "class_animation_player")
        == "Class Animation Player"
    )
