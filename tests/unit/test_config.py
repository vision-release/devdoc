from __future__ import annotations

from devdoc import config


def test_add_source_persists_source_metadata(isolated_devdoc_home):
    source = config.add_source("python", "https://docs.python.org", "web")

    assert source["name"] == "python"
    assert source["url"] == "https://docs.python.org"
    assert source["type"] == "web"
    assert source["path"].endswith("/docs/python")
    assert source["last_updated"] is None

    saved = config.get_source("python")
    assert saved is not None
    assert saved["name"] == "python"


def test_remove_source_returns_false_for_unknown_name(isolated_devdoc_home):
    assert config.remove_source("missing") is False


def test_update_source_metadata_writes_timestamp_and_commit(isolated_devdoc_home):
    config.add_source("godot", "https://github.com/godotengine/godot-docs.git", "git")

    config.update_source_timestamp("godot")
    config.update_source_commit("godot", "abc123")

    saved = config.get_source("godot")
    assert saved is not None
    assert saved["last_updated"] is not None
    assert saved["commit_hash"] == "abc123"
