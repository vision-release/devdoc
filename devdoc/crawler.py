"""Web and Git crawlers for documentation sources."""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Source type detection
# ---------------------------------------------------------------------------


def detect_source_type(url: str) -> str:
    """Detect whether a URL is a git repository or a website."""
    if url.endswith(".git"):
        return "git"
    parsed = urlparse(url)
    if parsed.netloc in ("github.com", "gitlab.com", "bitbucket.org"):
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) == 2:  # user/repo pattern
            return "git"
    return "web"


# ---------------------------------------------------------------------------
# Git crawler
# ---------------------------------------------------------------------------


def check_git_remote(url: str, stored_hash: str | None) -> tuple[bool, str]:
    """Check if the remote HEAD differs from the stored commit hash.

    Returns ``(needs_update, remote_hash)``.
    """
    r = subprocess.run(
        ["git", "ls-remote", url, "HEAD"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        # Can't determine remote state — assume update needed
        return True, ""
    remote_hash = r.stdout.split()[0]
    if stored_hash and remote_hash == stored_hash:
        return False, remote_hash
    return True, remote_hash


def crawl_git(source_info: dict, console: Console = _console) -> str | None:
    """Clone a git repo into a temp dir and copy only .md files to target.

    Returns the commit hash on success, or ``None`` on failure.
    """
    url = source_info["url"]
    target = Path(source_info["path"])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_clone = Path(tmp) / "repo"
        console.print(f"[yellow]Cloning [bold]{url}[/bold] …[/yellow]")
        r = subprocess.run(
            ["git", "clone", "--depth=1", url, str(tmp_clone)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            console.print(f"[red]git failed:[/red] {r.stderr.strip()}")
            return None

        # Get commit hash from the cloned repo
        r_hash = subprocess.run(
            ["git", "-C", str(tmp_clone), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        commit_hash = r_hash.stdout.strip() if r_hash.returncode == 0 else ""

        # Convert RST → Markdown inside the temp clone
        _convert_rst_files(tmp_clone, console)

        # Clear target and copy only .md files, preserving relative paths
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

        md_files = list(tmp_clone.rglob("*.md"))
        for md in md_files:
            rel = md.relative_to(tmp_clone)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md, dest)

    count = len(list(target.rglob("*.md")))
    console.print(
        f"[green]Repository ready — {count} Markdown files at {target}[/green]"
    )
    return commit_hash


def _convert_rst_files(base: Path, console: Console) -> None:
    rst_files = [f for f in base.rglob("*.rst") if not f.with_suffix(".md").exists()]
    if not rst_files:
        return

    try:
        has_pandoc = (
            subprocess.run(["pandoc", "--version"], capture_output=True).returncode == 0
        )
    except FileNotFoundError:
        has_pandoc = False
    converter = "pandoc" if has_pandoc else "built-in"
    console.print(
        f"[yellow]Converting {len(rst_files)} RST files ({converter})…[/yellow]"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Converting", total=len(rst_files))
        for rst in rst_files:
            md = rst.with_suffix(".md")
            if has_pandoc:
                subprocess.run(
                    ["pandoc", "-f", "rst", "-t", "markdown", str(rst), "-o", str(md)],
                    capture_output=True,
                )
            else:
                try:
                    md.write_text(
                        _rst_to_markdown(rst.read_text("utf-8", errors="ignore")),
                        "utf-8",
                    )
                except Exception:
                    pass
            progress.advance(task)


def _rst_to_markdown(text: str) -> str:
    """Minimal RST → Markdown fallback (no pandoc required)."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    level_map = {"=": "#", "-": "##", "~": "###", "^": "####", '"': "#####"}
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if (
            nxt
            and re.match(r"^[=\-~^\"']{3,}$", nxt.strip())
            and len(nxt.strip()) >= len(line.strip())
        ):
            level = level_map.get(nxt.strip()[0], "##")
            out.append(f"{level} {line.strip()}")
            i += 2
            continue
        out.append(line)
        i += 1
    text = "\n".join(out)
    text = re.sub(r"`([^`<]+)\s*<([^>]+)>`__?", r"[\1](\2)", text)
    text = re.sub(r"``([^`]+)``", r"`\1`", text)
    text = re.sub(r":[a-z_]+:`([^`]+)`", r"`\1`", text)
    text = re.sub(r"^\.\. [a-z_-]+::.*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:([^:]+):\s*", r"**\1**: ", text, flags=re.MULTILINE)
    return text


# ---------------------------------------------------------------------------
# Web crawler — powered by crawl4ai
# ---------------------------------------------------------------------------


def crawl_web(
    source_info: dict,
    max_pages: int = 500,
    max_depth: int = 5,
    delay: float = 0.0,
    console: Console = _console,
) -> bool:
    """Crawl a website with crawl4ai and save each page as Markdown."""
    try:
        return asyncio.run(
            _crawl_web_async(source_info, max_pages, max_depth, delay, console)
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Crawl interrupted by user.[/yellow]")
        return False


async def _crawl_web_async(
    source_info: dict,
    max_pages: int,
    max_depth: int,
    delay: float,
    console: Console,
) -> bool:
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from crawl4ai.deep_crawling import BFSDeepGraphCrawler
    except ImportError:
        console.print(
            "[red]crawl4ai not installed.[/red] Run:  uv tool install . --reinstall"
        )
        return False

    url = source_info["url"].rstrip("/") + "/"
    target = Path(source_info["path"])
    target.mkdir(parents=True, exist_ok=True)

    console.print(
        f"[yellow]Crawling [bold]{url}[/bold] "
        f"(max {max_pages} pages, depth {max_depth})…[/yellow]"
    )

    # Ensure crawl4ai playwright browsers are installed
    _ensure_playwright(console)

    browser_cfg = BrowserConfig(headless=True, verbose=False)
    crawl_cfg = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepGraphCrawler(
            max_depth=max_depth,
            max_pages=max_pages,
            filter_links=True,  # stay on same domain
        ),
        word_count_threshold=30,  # skip nearly-empty pages
        remove_overlay_elements=True,
        excluded_tags=["nav", "footer", "header", "aside"],
        delay_before_return_html=delay if delay > 0 else None,
        verbose=False,
    )

    saved = 0
    errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Crawling {url}", total=max_pages)

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            async for result in await crawler.arun(url=url, config=crawl_cfg):
                if not result.success:
                    errors += 1
                    continue

                markdown = _pick_markdown(result)
                if len(markdown.strip()) < 80:
                    continue

                page_url = result.url
                title = _result_title(result, page_url)
                filepath = _url_to_path(page_url, url, target)
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(
                    f"---\ntitle: {title}\nsource: {page_url}\n---\n\n{markdown}",
                    encoding="utf-8",
                )

                saved += 1
                progress.update(
                    task,
                    completed=saved,
                    description=f"Saving: …{page_url[-50:]}",
                )

    console.print(
        f"[green]Saved {saved} pages → {target}[/green]"
        + (f"  [dim]({errors} errors)[/dim]" if errors else "")
    )
    return saved > 0


def _ensure_playwright(console: Console) -> None:
    """Install playwright browsers if missing (one-time setup)."""
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "already installed" not in result.stderr:
        console.print("[dim]playwright install output:[/dim]")
        console.print(f"[dim]{result.stdout[:200]}[/dim]")


def _pick_markdown(result) -> str:
    """Extract best markdown string from a crawl4ai CrawlResult."""
    md = getattr(result, "markdown", None)
    if md is None:
        return ""
    # crawl4ai ≥0.4 wraps in a MarkdownGenerationResult object
    if hasattr(md, "fit_markdown") and md.fit_markdown:
        return md.fit_markdown
    if hasattr(md, "raw_markdown"):
        return md.raw_markdown
    # older versions return a plain string
    return str(md)


def _result_title(result, url: str) -> str:
    meta = getattr(result, "metadata", {}) or {}
    title = meta.get("title") or meta.get("og:title") or ""
    if title:
        return title.split("|")[0].split("—")[0].strip()
    return (
        urlparse(url).path.strip("/").split("/")[-1].replace("-", " ").title()
        or "index"
    )


def _url_to_path(page_url: str, base_url: str, target: Path) -> Path:
    """Map a crawled URL to a local .md file path."""
    base_parsed = urlparse(base_url)
    page_parsed = urlparse(page_url)

    rel = page_parsed.path.strip("/")
    base_rel = base_parsed.path.strip("/")
    if rel.startswith(base_rel):
        rel = rel[len(base_rel) :].strip("/")
    if not rel:
        rel = "index"

    # Flatten to avoid deep nesting: a/b/c → a__b__c.md
    rel = rel.replace("/", "__")
    if not rel.endswith(".md"):
        rel += ".md"
    return target / rel
