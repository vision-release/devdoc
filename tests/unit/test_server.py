from __future__ import annotations

from pathlib import Path

from devdoc import server


def test_list_sources_reports_empty_state(monkeypatch):
    monkeypatch.setattr(server.config, "list_sources", lambda: {})

    result = server.list_sources()

    assert "No documentation sources configured." in result


def test_get_document_reads_source_file(monkeypatch, tmp_path: Path):
    source_dir = tmp_path / "python"
    source_dir.mkdir()
    file_path = source_dir / "guide.md"
    file_path.write_text("# Guide\n\ncontent", encoding="utf-8")

    monkeypatch.setattr(
        server.config,
        "list_sources",
        lambda: {
            "python": {
                "path": str(source_dir),
                "url": "https://docs.python.org",
                "type": "web",
            }
        },
    )

    result = server.get_document("python/guide.md")

    assert "# guide" in result.lower()
    assert "content" in result


def test_list_documents_lists_matching_files(monkeypatch, tmp_path: Path):
    source_dir = tmp_path / "python"
    tutorial_dir = source_dir / "tutorials"
    tutorial_dir.mkdir(parents=True)
    (tutorial_dir / "intro.md").write_text("# Intro", encoding="utf-8")

    monkeypatch.setattr(
        server.config,
        "list_sources",
        lambda: {
            "python": {
                "path": str(source_dir),
                "url": "https://docs.python.org",
                "type": "web",
            }
        },
    )

    result = server.list_documents("python", "tutorials")

    assert "python/tutorials/intro.md" in result
