"""Configuration and source management for devdoc."""

import json
from datetime import datetime
from pathlib import Path

DEVDOC_HOME = Path.home() / ".devdoc"
CONFIG_FILE = DEVDOC_HOME / "sources.json"
DOCS_DIR = DEVDOC_HOME / "docs"


def ensure_dirs():
    DEVDOC_HOME.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)


def load_config() -> dict:
    ensure_dirs()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"sources": {}}


def save_config(config: dict):
    ensure_dirs()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def add_source(name: str, url: str, source_type: str) -> dict:
    config = load_config()
    config["sources"][name] = {
        "name": name,
        "url": url,
        "type": source_type,
        "path": str(DOCS_DIR / name),
        "added": datetime.now().isoformat(),
        "last_updated": None,
    }
    save_config(config)
    return config["sources"][name]


def get_source(name: str) -> dict | None:
    return load_config()["sources"].get(name)


def list_sources() -> dict:
    return load_config()["sources"]


def remove_source(name: str) -> bool:
    config = load_config()
    if name in config["sources"]:
        del config["sources"][name]
        save_config(config)
        return True
    return False


def update_source_timestamp(name: str):
    config = load_config()
    if name in config["sources"]:
        config["sources"][name]["last_updated"] = datetime.now().isoformat()
        save_config(config)


def update_source_commit(name: str, commit_hash: str):
    config = load_config()
    if name in config["sources"]:
        config["sources"][name]["commit_hash"] = commit_hash
        save_config(config)
