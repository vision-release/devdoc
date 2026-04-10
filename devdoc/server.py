"""MCP server exposing documentation tools."""

from __future__ import annotations

import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import config, search as search_module

# Message logging mode: "none", "incoming", "outgoing", "both"
_log_messages: str = "none"


def _log_incoming(tool_name: str, kwargs: dict):
    if _log_messages not in ("incoming", "both"):
        return
    ts = datetime.now().strftime("%H:%M:%S")
    args = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    print(f"[{ts}] ← {tool_name}({args})", file=sys.stderr, flush=True)


def _log_outgoing(tool_name: str, result: str):
    if _log_messages not in ("outgoing", "both"):
        return
    ts = datetime.now().strftime("%H:%M:%S")
    preview = textwrap.shorten(result, width=200, placeholder="…")
    print(f"[{ts}] → {tool_name} response ({len(result)} chars): {preview}", file=sys.stderr, flush=True)

mcp = FastMCP(
    "DevDoc",
    instructions=(
        "Documentation search service. "
        "Use list_sources to see available docs, search_docs to find relevant pages, "
        "get_document to read full content, and list_documents to browse by path."
    ),
)

# Lazy-loaded index — rebuilt automatically when sources change
_index: Optional[search_module.DocumentIndex] = None
_index_source_keys: Optional[frozenset] = None


def _get_index() -> search_module.DocumentIndex:
    global _index, _index_source_keys
    sources = config.list_sources()
    current_keys = frozenset(sources.keys())
    if _index is None or current_keys != _index_source_keys:
        _index_source_keys = current_keys
        _index = search_module.build_index(sources)
    return _index


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_sources() -> str:
    """List all configured documentation sources with document counts."""
    _log_incoming("list_sources", {})
    sources = config.list_sources()
    if not sources:
        return (
            "No documentation sources configured.\n"
            "Add one with: devdoc add <name> <url>"
        )

    lines = [f"Available documentation sources ({len(sources)} total):\n"]
    for name, info in sources.items():
        p = Path(info["path"])
        count = len(list(p.rglob("*.md"))) if p.exists() else 0
        updated = (info.get("last_updated") or "never").split("T")[0]
        lines.append(f"- **{name}** `{info['type']}` — {count} docs — updated: {updated}")
        lines.append(f"  {info['url']}")
    result = "\n".join(lines)
    _log_outgoing("list_sources", result)
    return result


@mcp.tool()
def search_docs(query: str, source: Optional[str] = None) -> str:
    """
    Search documentation by keywords and return matching excerpts.

    Args:
        query: Keywords or phrases to search for.
        source: Limit results to a specific source (optional).
    """
    _log_incoming("search_docs", {"query": query, "source": source})
    index = _get_index()
    results = index.search(query, source=source, max_results=10)

    if not results:
        suffix = f" in '{source}'" if source else ""
        return f"No results found for '{query}'{suffix}."

    lines = [f"**{len(results)} results for '{query}'**\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r['title']}")
        lines.append(f"- Source: `{r['source']}`")
        lines.append(f"- Path: `{r['path']}`")
        lines.append(f"\n{r['snippet']}\n")
    result = "\n".join(lines)
    _log_outgoing("search_docs", result)
    return result


@mcp.tool()
def get_document(path: str) -> str:
    """
    Return the full content of a documentation file.

    Args:
        path: Document path in 'source/relative/file.md' format
              (as returned by search_docs or list_documents).
    """
    _log_incoming("get_document", {"path": path})
    sources = config.list_sources()
    parts = path.split("/", 1)
    if len(parts) != 2:
        return f"Invalid path '{path}'. Expected format: source/relative/path.md"

    source_name, rel = parts
    if source_name not in sources:
        return f"Unknown source '{source_name}'. Run list_sources to see available sources."

    file_path = Path(sources[source_name]["path"]) / rel
    # Try .md then .rst fallback
    if not file_path.exists() and file_path.suffix == ".md":
        alt = file_path.with_suffix(".rst")
        if alt.exists():
            file_path = alt

    if not file_path.exists():
        return f"File not found: {path}"

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        result = f"# {file_path.stem}\n\n**Path:** `{path}`\n\n---\n\n{content}"
        _log_outgoing("get_document", result)
        return result
    except Exception as exc:
        return f"Error reading '{path}': {exc}"


@mcp.tool()
def list_documents(source: str, path: str = "") -> str:
    """
    List documents in a source, optionally filtered by sub-path.

    Args:
        source: Source name (from list_sources).
        path: Optional sub-path prefix for filtering (e.g. 'tutorials').
    """
    _log_incoming("list_documents", {"source": source, "path": path})
    sources = config.list_sources()
    if source not in sources:
        available = ", ".join(sources) or "(none)"
        return f"Source '{source}' not found. Available: {available}"

    base = Path(sources[source]["path"])
    if not base.exists():
        return f"No local docs for '{source}'. Run: devdoc update {source}"

    search_root = (base / path) if path else base
    md_files = sorted(search_root.rglob("*.md"))
    rst_only = sorted(
        f for f in search_root.rglob("*.rst") if not f.with_suffix(".md").exists()
    )
    all_files = md_files + rst_only

    if not all_files:
        suffix = f"/{path}" if path else ""
        return f"No documents found in '{source}{suffix}'."

    suffix = f"/{path}" if path else ""
    lines = [f"**{source}{suffix}** — {len(all_files)} documents\n"]
    for f in all_files[:150]:
        rel = str(f.relative_to(base))
        lines.append(f"- `{source}/{rel}`")
    if len(all_files) > 150:
        lines.append(f"\n_…and {len(all_files) - 150} more files_")
    result = "\n".join(lines)
    _log_outgoing("list_documents", result)
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(transport: str = "stdio", host: str = "0.0.0.0", port: int = 8080,
        log_messages: str = "none"):
    global _log_messages
    _log_messages = log_messages
    parts = [f"[devdoc] MCP server starting ({transport})"]
    if log_messages != "none":
        parts.append(f"  message logging: {log_messages}")
    print("\n".join(parts), file=sys.stderr, flush=True)
    if transport == "sse":
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
