from __future__ import annotations

from pathlib import Path

import pytest

from devdoc import config


@pytest.fixture()
def isolated_devdoc_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    home = tmp_path / ".devdoc"
    docs = home / "docs"
    config_file = home / "sources.json"

    monkeypatch.setattr(config, "DEVDOC_HOME", home)
    monkeypatch.setattr(config, "DOCS_DIR", docs)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)

    return home
