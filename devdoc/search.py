"""Document indexing and keyword search."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Optional


class DocumentIndex:
    """In-memory keyword index over documentation files."""

    def __init__(self):
        self._docs: dict[str, dict] = {}  # doc_path -> meta
        self._word_index: defaultdict[str, set] = defaultdict(set)

    # ------------------------------------------------------------------
    def add_document(self, doc_path: str, content: str, source: str, title: str = ""):
        self._docs[doc_path] = {
            "path": doc_path,
            "title": title or doc_path.rsplit("/", 1)[-1],
            "content": content,
            "source": source,
        }
        for word in self._tokenize(content + " " + title):
            self._word_index[word].add(doc_path)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", text.lower())

    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        source: Optional[str] = None,
        max_results: int = 10,
    ) -> list[dict]:
        query_words = self._tokenize(query)
        if not query_words:
            return []

        scores: defaultdict[str, float] = defaultdict(float)
        for word in query_words:
            for doc_path in self._word_index.get(word, set()):
                doc = self._docs[doc_path]
                if source and doc["source"] != source:
                    continue
                content_lower = doc["content"].lower()
                freq = content_lower.count(word)
                scores[doc_path] += freq
                if word in doc["title"].lower():
                    scores[doc_path] += 20

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                **{k: v for k, v in self._docs[p].items() if k != "content"},
                "score": score,
                "snippet": self._snippet(self._docs[p]["content"], query_words),
            }
            for p, score in ranked[:max_results]
        ]

    def _snippet(self, content: str, words: list[str], length: int = 400) -> str:
        lower = content.lower()
        pos = len(content)
        for w in words:
            idx = lower.find(w)
            if idx != -1 and idx < pos:
                pos = idx
        if pos == len(content):
            pos = 0
        start = max(0, pos - 60)
        end = min(len(content), pos + length)
        snippet = content[start:end]
        if start:
            snippet = "…" + snippet
        if end < len(content):
            snippet += "…"
        return snippet

    # ------------------------------------------------------------------
    @property
    def document_count(self) -> int:
        return len(self._docs)


def build_index(sources: dict) -> DocumentIndex:
    """Build a fresh index from all downloaded documentation files."""
    index = DocumentIndex()
    for source_name, source_info in sources.items():
        source_path = Path(source_info["path"])
        if not source_path.exists():
            continue

        md_files = list(source_path.rglob("*.md"))
        # Include RST files that were not converted
        rst_only = [
            f for f in source_path.rglob("*.rst") if not f.with_suffix(".md").exists()
        ]

        for file in md_files + rst_only:
            try:
                content = file.read_text(encoding="utf-8", errors="ignore")
                title = _extract_title(content, file.stem)
                rel = str(file.relative_to(source_path))
                doc_path = f"{source_name}/{rel}"
                index.add_document(doc_path, content, source_name, title)
            except Exception:
                pass

    return index


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines()[:15]:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("title:"):
            return line[6:].strip().strip('"').strip("'")
    return fallback.replace("_", " ").replace("-", " ").title()
