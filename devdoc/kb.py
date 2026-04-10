"""Knowledge base: curated public documentation sources."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

_CSV_PATH = Path(__file__).parent / "knowledge.csv"

# Cached entries: key -> dict
_cache: dict[str, dict] | None = None


def _load() -> dict[str, dict]:
    global _cache
    if _cache is not None:
        return _cache
    _cache = {}
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            _cache[row["key"].strip()] = {k: v.strip() for k, v in row.items()}
    return _cache


def lookup(key: str) -> Optional[dict]:
    """Return the KB entry for *key*, or None if not found."""
    return _load().get(key.lower().strip())


def all_entries() -> list[dict]:
    """Return all KB entries sorted by category then key."""
    return sorted(_load().values(), key=lambda e: (e["category"], e["key"]))


def search(query: str) -> list[dict]:
    """Case-insensitive substring search across key, name, description."""
    q = query.lower()
    return [
        e for e in all_entries()
        if q in e["key"] or q in e["name"].lower() or q in e["description"].lower()
    ]


def keys() -> list[str]:
    return sorted(_load().keys())


def categories() -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for e in all_entries():
        c = e["category"]
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result
