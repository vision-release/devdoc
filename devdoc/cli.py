"""CLI entry point for devdoc."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import config
from . import kb as kb_module

out = Console(stderr=False)  # normal output
err = Console(stderr=True)  # status / progress


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _human_size(total_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if total_bytes < 1024:
            return f"{total_bytes:.1f} {unit}"
        total_bytes /= 1024
    return f"{total_bytes:.1f} TB"


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _count_files(path: Path) -> int:
    return len(list(path.rglob("*.md")))


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option("0.1.0", prog_name="devdoc")
def main():
    """DevDoc — Documentation MCP service for local LLMs and agents.\n
    \b
    Quick start (knowledge base):
      devdoc add godot
      devdoc add roblox

    Quick start (custom URL):
      devdoc add godot https://github.com/godotengine/godot-docs.git
      devdoc start
    """


# ---------------------------------------------------------------------------
# devdoc add
# ---------------------------------------------------------------------------


@main.command()
@click.argument("name")
@click.argument("url", required=False, default=None)
@click.option(
    "--max-pages",
    default=500,
    show_default=True,
    help="Maximum pages to crawl (web sources only).",
)
@click.option(
    "--delay",
    default=0.5,
    show_default=True,
    help="Seconds between requests (web sources only).",
)
@click.option(
    "--type",
    "source_type",
    default=None,
    type=click.Choice(["git", "web"]),
    help="Force source type (auto-detected by default).",
)
def add(
    name: str, url: str | None, max_pages: int, delay: float, source_type: str | None
):
    """Add a documentation source and download it.\n
    Omit URL to look up the source in the built-in knowledge base.\n
    \b
    Knowledge base (no URL needed):
      devdoc add godot
      devdoc add roblox
      devdoc add react
      devdoc add deno

    Custom URL:
      devdoc add mylib https://docs.example.com/
      devdoc add myrepo https://github.com/org/repo.git

    Browse the knowledge base:
      devdoc kb
    """
    kb_entry: dict | None = None

    if url is None:
        # ── Knowledge base lookup ──────────────────────────────────────────
        kb_entry = kb_module.lookup(name)
        if kb_entry is None:
            err.print(
                f"[red bold]✗ '{name}' not found in the knowledge base.[/red bold]"
            )
            # Suggest close matches
            matches = kb_module.search(name)
            if matches:
                err.print("\n[yellow]Did you mean one of these?[/yellow]")
                for m in matches[:5]:
                    description = m["description"][:60]
                    err.print(
                        f"  [cyan]{m['key']}[/cyan]  "
                        f"{m['name']}  [dim]{description}[/dim]"
                    )
            else:
                err.print("\nBrowse all available sources:  [bold]devdoc kb[/bold]")
            sys.exit(1)

        url = kb_entry["url"]
        stype = source_type or kb_entry["type"]
        disp_name = kb_entry["name"]
        err.print(
            f"[bold]Knowledge base:[/bold] [cyan]{name}[/cyan] → "
            f"[green]{disp_name}[/green]  ([dim]{kb_entry['category']}[/dim])"
        )
    else:
        from .crawler import detect_source_type

        stype = source_type or detect_source_type(url)
        disp_name = name

    err.print(f"[bold]Adding[/bold] [cyan]{name}[/cyan] ([green]{stype}[/green])")
    err.print(f"[dim]  {url}[/dim]\n")

    source_info = config.add_source(name, url, stype)

    if stype == "git":
        from .crawler import crawl_git

        commit_hash = crawl_git(source_info, console=err)
        ok = commit_hash is not None
        if ok and commit_hash:
            config.update_source_commit(name, commit_hash)
    else:
        from .crawler import crawl_web

        ok = crawl_web(source_info, max_pages=max_pages, delay=delay, console=err)

    if ok:
        config.update_source_timestamp(name)
        err.print(f"\n[green bold]✓ '{name}' added successfully.[/green bold]")
        err.print("[dim]Start the MCP server:  devdoc start[/dim]")
    else:
        err.print(f"\n[red bold]✗ Failed to add '{name}'.[/red bold]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# devdoc list  — full information about every source
# ---------------------------------------------------------------------------


@main.command("list")
def list_cmd():
    """List all configured documentation sources with full details."""
    sources = config.list_sources()
    if not sources:
        out.print("[yellow]No sources configured.[/yellow]")
        out.print("Add one with:  [bold]devdoc add <name> <url>[/bold]")
        return

    t = Table(title="DevDoc Sources", show_lines=True, expand=True)
    t.add_column("Name", style="cyan bold", no_wrap=True)
    t.add_column("Type", style="green", no_wrap=True)
    t.add_column("Docs", justify="right", no_wrap=True)
    t.add_column("Size", justify="right", no_wrap=True)
    t.add_column("Added", no_wrap=True)
    t.add_column("Updated", no_wrap=True)
    t.add_column("URL")

    for name, info in sources.items():
        p = Path(info["path"])
        if p.exists():
            doc_str = str(_count_files(p))
            size_str = _human_size(_dir_size(p))
        else:
            doc_str = "[red]–[/red]"
            size_str = "–"

        added = (info.get("added") or "–").split("T")[0]
        updated = (info.get("last_updated") or "never").split("T")[0]
        url = info["url"]
        if len(url) > 60:
            url = url[:57] + "…"

        t.add_row(name, info["type"], doc_str, size_str, added, updated, url)

    out.print(t)


# ---------------------------------------------------------------------------
# devdoc kb  — browse the built-in knowledge base
# ---------------------------------------------------------------------------

_CATEGORY_COLORS = {
    "gamedev": "magenta",
    "frontend": "cyan",
    "backend": "green",
    "language": "yellow",
    "graphics": "blue",
    "mobile": "bright_cyan",
    "desktop": "bright_blue",
    "testing": "bright_yellow",
    "api": "bright_green",
    "web": "bright_white",
}


def _cat_color(cat: str) -> str:
    return _CATEGORY_COLORS.get(cat, "white")


@main.command("kb")
@click.argument("query", required=False, default=None)
@click.option(
    "--category",
    "-c",
    default=None,
    help="Filter by category (gamedev, frontend, backend, …).",
)
def kb(query: str | None, category: str | None):
    """Browse the built-in documentation knowledge base.\n
    \b
    Examples:
      devdoc kb                  # show everything
      devdoc kb godot            # search by name or keyword
      devdoc kb -c gamedev       # filter by category
      devdoc kb -c frontend
    """
    if query:
        entries = kb_module.search(query)
        if not entries:
            out.print(f"[yellow]No knowledge base entries matching '{query}'.[/yellow]")
            return
    else:
        entries = kb_module.all_entries()

    if category:
        entries = [e for e in entries if e["category"] == category.lower()]
        if not entries:
            cats = ", ".join(kb_module.categories())
            out.print(f"[yellow]No entries for category '{category}'.[/yellow]")
            out.print(f"Available categories: {cats}")
            return

    # Group by category for nicer display
    from collections import defaultdict

    grouped: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        grouped[e["category"]].append(e)

    for cat, cat_entries in sorted(grouped.items()):
        color = _cat_color(cat)
        t = Table(
            title=f"[{color}]{cat}[/{color}]",
            show_header=True,
            show_lines=False,
            expand=True,
            title_justify="left",
        )
        t.add_column("Key", style=f"{color} bold", no_wrap=True, width=14)
        t.add_column("Name", no_wrap=True, width=20)
        t.add_column("Type", width=5)
        t.add_column("Description")

        for e in cat_entries:
            t.add_row(e["key"], e["name"], e["type"], e["description"])

        out.print(t)

    total = len(entries)
    out.print(
        f"\n[dim]{total} entries — use "
        "[bold]devdoc add <key>[/bold] to download any of them[/dim]"
    )


# ---------------------------------------------------------------------------
# devdoc status  — overall health of the devdoc installation
# ---------------------------------------------------------------------------


@main.command()
def status():
    """Show overall devdoc installation and source health."""
    import shutil as sh

    sources = config.list_sources()
    docs_dir = config.DOCS_DIR

    # Header panel
    devdoc_bin = sh.which("devdoc") or "devdoc (not in PATH)"
    total_docs = 0
    total_bytes = 0
    for info in sources.values():
        p = Path(info["path"])
        if p.exists():
            total_docs += _count_files(p)
            total_bytes += _dir_size(p)

    header = (
        f"[bold cyan]DevDoc[/bold cyan] v0.1.0\n"
        f"Binary : [dim]{devdoc_bin}[/dim]\n"
        f"Config : [dim]{config.CONFIG_FILE}[/dim]\n"
        f"Docs   : [dim]{docs_dir}[/dim]\n"
        f"Sources: [bold]{len(sources)}[/bold]  |  "
        f"Total docs: [bold]{total_docs}[/bold]  |  "
        f"Disk: [bold]{_human_size(total_bytes)}[/bold]"
    )
    out.print(Panel(header, title="Status", border_style="cyan"))

    if not sources:
        out.print("[yellow]No sources configured.[/yellow]")
        out.print("  devdoc add <name> <url>")
        return

    # Per-source health table
    t = Table(show_header=True, show_lines=False, expand=True)
    t.add_column("Source", style="cyan bold", no_wrap=True)
    t.add_column("Type", style="green", no_wrap=True)
    t.add_column("State")
    t.add_column("Docs", justify="right")
    t.add_column("Size", justify="right")
    t.add_column("Updated", no_wrap=True)

    for name, info in sources.items():
        p = Path(info["path"])
        if not p.exists():
            state = "[red]missing[/red]"
            doc_str = "–"
            size_str = "–"
        else:
            doc_str = str(_count_files(p))
            size_str = _human_size(_dir_size(p))
            commit = info.get("commit_hash", "")
            if info["type"] == "git" and commit:
                state = f"[green]ok[/green]  [dim]@ {commit[:10]}[/dim]"
            else:
                state = "[green]ok[/green]"

        updated = (info.get("last_updated") or "never").split("T")[0]
        t.add_row(name, info["type"], state, doc_str, size_str, updated)

    out.print(t)


# ---------------------------------------------------------------------------
# devdoc info <name>  — detailed view of one source
# ---------------------------------------------------------------------------


@main.command()
@click.argument("name")
def info(name: str):
    """Show detailed information about a single documentation source."""
    sources = config.list_sources()
    if name not in sources:
        out.print(f"[red]Source '{name}' not found.[/red]")
        out.print(f"Known sources: {', '.join(sources) or '(none)'}")
        sys.exit(1)

    src = sources[name]
    path = Path(src["path"])

    lines: list[str] = [
        f"[bold cyan]{name}[/bold cyan]",
        f"  Type    : [green]{src['type']}[/green]",
        f"  URL     : {src['url']}",
        f"  Path    : [dim]{path}[/dim]",
        f"  Added   : {(src.get('added') or '–').split('T')[0]}",
        f"  Updated : {(src.get('last_updated') or 'never').split('T')[0]}",
    ]

    if not path.exists():
        lines.append(
            "  [red]Local files not found — run: devdoc update " + name + "[/red]"
        )
        out.print(Panel("\n".join(lines), title="Source Info", border_style="cyan"))
        return

    doc_count = _count_files(path)
    size = _dir_size(path)
    lines += [
        "",
        f"  Markdown files : [bold]{doc_count}[/bold]",
        f"  Disk usage     : [bold]{_human_size(size)}[/bold]",
    ]

    # Git-specific extras
    if src["type"] == "git":
        commit = src.get("commit_hash", "")
        if commit:
            lines.append(f"  Commit  : [dim]{commit}[/dim]")

    # Top-level directory structure (max 10 entries)
    top = sorted(p for p in path.iterdir() if not p.name.startswith("."))[:10]
    if top:
        lines.append("")
        lines.append("  Contents:")
        for entry in top:
            icon = "📁" if entry.is_dir() else "📄"
            sub = f"  ({len(list(entry.rglob('*.md')))} md)" if entry.is_dir() else ""
            lines.append(f"    {icon} {entry.name}{sub}")
        remaining = len(list(p for p in path.iterdir())) - len(top)
        if remaining > 0:
            lines.append(f"    … and {remaining} more")

    out.print(Panel("\n".join(lines), title=f"info: {name}", border_style="cyan"))


# ---------------------------------------------------------------------------
# devdoc update
# ---------------------------------------------------------------------------


@main.command()
@click.argument("name", required=False)
@click.option("--max-pages", default=500, show_default=True)
@click.option("--delay", default=0.5, show_default=True)
def update(name: str | None, max_pages: int, delay: float):
    """Update one or all documentation sources."""
    from .crawler import check_git_remote, crawl_git, crawl_web

    sources = config.list_sources()
    if not sources:
        err.print("[yellow]No sources configured.[/yellow]")
        return

    if name and name not in sources:
        err.print(f"[red]Source '{name}' not found.[/red]")
        sys.exit(1)

    targets = {name: sources[name]} if name else sources

    for src_name, info in targets.items():
        err.print(f"\n[bold]Updating [cyan]{src_name}[/cyan]…[/bold]")
        if info["type"] == "git":
            stored_hash = info.get("commit_hash")
            needs_update, remote_hash = check_git_remote(info["url"], stored_hash)
            if not needs_update:
                short_hash = (stored_hash or "")[:10]
                err.print(
                    f"[green]✓ {src_name} already up-to-date[/green]  "
                    f"[dim]({short_hash})[/dim]"
                )
                continue
            commit_hash = crawl_git(info, console=err)
            ok = commit_hash is not None
            if ok and commit_hash:
                config.update_source_commit(src_name, commit_hash)
        else:
            ok = crawl_web(info, max_pages=max_pages, delay=delay, console=err)
        if ok:
            config.update_source_timestamp(src_name)
            err.print(f"[green]✓ {src_name} updated[/green]")
        else:
            err.print(f"[red]✗ Failed to update {src_name}[/red]")


# ---------------------------------------------------------------------------
# devdoc remove
# ---------------------------------------------------------------------------


@main.command()
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
def remove(name: str, yes: bool):
    """Remove a documentation source and its local files."""
    sources = config.list_sources()
    if name not in sources:
        err.print(f"[red]Source '{name}' not found.[/red]")
        sys.exit(1)

    if not yes:
        click.confirm(f"Remove '{name}' and delete all downloaded files?", abort=True)

    src_path = Path(sources[name]["path"])
    if src_path.exists():
        shutil.rmtree(src_path)
    config.remove_source(name)
    out.print(f"[green]✓ Removed '{name}'[/green]")


# Short alias
@main.command("rm", hidden=False)
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
@click.pass_context
def rm(ctx: click.Context, name: str, yes: bool):
    """Alias for 'remove'. Remove a source and its local files."""
    ctx.invoke(remove, name=name, yes=yes)


# ---------------------------------------------------------------------------
# devdoc start
# ---------------------------------------------------------------------------

_PID_FILE = config.DEVDOC_HOME / "devdoc.pid"
_LOG_FILE = config.DEVDOC_HOME / "devdoc.log"


def _daemon_running() -> int | None:
    """Return PID if the daemon is running, else None."""
    import os

    if not _PID_FILE.exists():
        return None
    try:
        pid = int(_PID_FILE.read_text().strip())
        os.kill(pid, 0)  # signal 0 = just check existence
        return pid
    except (ValueError, OSError):
        return None


@main.command()
@click.option(
    "--transport",
    default="stdio",
    type=click.Choice(["stdio", "sse"]),
    show_default=True,
    help="MCP transport: stdio (default) or sse (HTTP/SSE).",
)
@click.option(
    "--host", default="0.0.0.0", show_default=True, help="Bind host (SSE mode only)."
)
@click.option(
    "--port", default=8080, show_default=True, help="Bind port (SSE mode only)."
)
@click.option(
    "--daemon",
    "-d",
    is_flag=True,
    help="Run as a background daemon (SSE transport only).",
)
@click.option(
    "--log-messages",
    default="none",
    type=click.Choice(["none", "incoming", "outgoing", "both"]),
    show_default=True,
    help="Log MCP messages to stderr (none, incoming, outgoing, both).",
)
def start(transport: str, host: str, port: int, daemon: bool, log_messages: str):
    """Start the MCP server.\n
    \b
    For Claude Desktop / local LLMs (default):
      devdoc start

    For HTTP/SSE agents:
      devdoc start --transport sse --port 8080

    As a background daemon:
      devdoc start --transport sse --daemon
      devdoc stop
      devdoc logs
    """
    if daemon:
        if transport != "sse":
            err.print("[red]--daemon requires --transport sse[/red]")
            sys.exit(1)

        pid = _daemon_running()
        if pid:
            err.print(f"[yellow]Daemon already running (PID {pid}).[/yellow]")
            err.print("[dim]Stop with:  devdoc stop[/dim]")
            sys.exit(1)

        config.ensure_dirs()
        devdoc_bin = shutil.which("devdoc") or sys.argv[0]
        cmd = [
            devdoc_bin,
            "start",
            "--transport",
            "sse",
            "--host",
            host,
            "--port",
            str(port),
            "--log-messages",
            log_messages,
        ]

        with open(_LOG_FILE, "a") as log_f:
            proc = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=log_f,
                start_new_session=True,
            )

        _PID_FILE.write_text(str(proc.pid))
        err.print(f"[green bold]✓ DevDoc daemon started[/green bold]  (PID {proc.pid})")
        err.print(f"  [cyan]SSE endpoint:[/cyan]  http://{host}:{port}/sse")
        err.print(f"  [cyan]Log:[/cyan]           {_LOG_FILE}")
        err.print("  [dim]Stop with:     devdoc stop[/dim]")
        err.print("  [dim]Follow logs:   devdoc logs[/dim]")
        return

    sources = config.list_sources()
    if not sources:
        err.print(
            "[yellow]Warning: no sources configured — server will start empty.[/yellow]"
        )
        err.print("[dim]  devdoc add <name> <url>[/dim]\n")
    else:
        err.print(
            f"[bold]Starting DevDoc MCP ({transport}) with "
            f"{len(sources)} source(s):[/bold]"
        )
        for src_name, info in sources.items():
            p = Path(info["path"])
            count = len(list(p.rglob("*.md"))) if p.exists() else 0
            err.print(f"  [cyan]•[/cyan] {src_name}: {count} docs")
        if transport == "sse":
            err.print(f"\n[dim]Listening on http://{host}:{port}[/dim]")
        err.print()

    if log_messages != "none":
        err.print(f"  [dim]Message logging:[/dim] {log_messages}")

    from .server import run

    run(transport=transport, host=host, port=port, log_messages=log_messages)


# ---------------------------------------------------------------------------
# devdoc stop  — stop the background daemon
# ---------------------------------------------------------------------------


@main.command()
def stop():
    """Stop the background MCP daemon."""
    import os
    import signal

    pid = _daemon_running()
    if pid is None:
        if _PID_FILE.exists():
            err.print(
                "[yellow]Stale PID file — daemon is not running. Cleaning up.[/yellow]"
            )
            _PID_FILE.unlink()
        else:
            err.print("[yellow]Daemon is not running.[/yellow]")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        _PID_FILE.unlink(missing_ok=True)
        err.print(f"[green]✓ Daemon stopped (PID {pid})[/green]")
    except PermissionError:
        err.print(f"[red]Permission denied to stop PID {pid}[/red]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# devdoc logs  — tail the daemon log
# ---------------------------------------------------------------------------


@main.command()
@click.option("--lines", "-n", default=50, show_default=True, help="Lines to show.")
@click.option("--follow", "-f", is_flag=True, help="Follow log output (like tail -f).")
def logs(lines: int, follow: bool):
    """Show or follow the daemon log file."""
    if not _LOG_FILE.exists():
        err.print(f"[yellow]No log file found at {_LOG_FILE}[/yellow]")
        err.print(
            "[dim]Start the daemon first:  devdoc start --transport sse --daemon[/dim]"
        )
        return

    pid = _daemon_running()
    status = (
        f"[green]running (PID {pid})[/green]" if pid else "[yellow]stopped[/yellow]"
    )
    err.print(f"[bold]DevDoc daemon:[/bold] {status}  [dim]{_LOG_FILE}[/dim]\n")

    if follow:
        try:
            subprocess.run(["tail", f"-n{lines}", "-f", str(_LOG_FILE)])
        except KeyboardInterrupt:
            pass
    else:
        subprocess.run(["tail", f"-n{lines}", str(_LOG_FILE)])


# ---------------------------------------------------------------------------
# devdoc search  (quick local test, no MCP client needed)
# ---------------------------------------------------------------------------


@main.command()
@click.argument("query")
@click.option("--source", "-s", default=None, help="Limit to a specific source.")
@click.option("--limit", "-n", default=10, show_default=True)
def search(query: str, source: str | None, limit: int):
    """Search documentation locally (no MCP client needed)."""
    from . import search as search_module

    sources = config.list_sources()
    if not sources:
        out.print("[yellow]No sources configured.[/yellow]")
        return

    index = search_module.build_index(sources)
    results = index.search(query, source=source, max_results=limit)

    if not results:
        out.print(f"[yellow]No results for '{query}'[/yellow]")
        return

    out.print(f"\n[bold]Results for '[cyan]{query}[/cyan]':[/bold]\n")
    for i, r in enumerate(results, 1):
        out.print(f"[cyan bold]{i}. {r['title']}[/cyan bold]")
        out.print(f"   [dim]{r['path']}[/dim]")
        out.print(f"   {r['snippet'][:300]}\n")


# ---------------------------------------------------------------------------
# devdoc mcp-config  (print client configuration snippet)
# ---------------------------------------------------------------------------


@main.command("mcp-config")
@click.option("--transport", default="stdio", type=click.Choice(["stdio", "sse"]))
@click.option("--port", default=8080)
def mcp_config(transport: str, port: int):
    """Print an MCP client configuration snippet (Claude Desktop, etc.)."""
    import json
    import shutil as sh

    devdoc_bin = sh.which("devdoc") or "devdoc"

    if transport == "stdio":
        cfg = {
            "mcpServers": {
                "devdoc": {
                    "command": devdoc_bin,
                    "args": ["start"],
                }
            }
        }
    else:
        cfg = {
            "mcpServers": {
                "devdoc": {
                    "url": f"http://localhost:{port}/sse",
                }
            }
        }

    out.print("[bold]Add to your MCP client config:[/bold]\n")
    out.print(json.dumps(cfg, indent=2))


# ---------------------------------------------------------------------------
# devdoc completion  — install shell tab completion
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--shell",
    default=None,
    type=click.Choice(["bash", "zsh", "fish"]),
    help="Shell type (auto-detected if not specified).",
)
@click.option(
    "--install", is_flag=True, help="Write the completion hook to your shell profile."
)
def completion(shell: str | None, install: bool):
    """Enable shell tab completion for devdoc.\n
    \b
    Auto-install (detects shell):
      devdoc completion --install

    Manual bash:
      echo 'eval "$(_DEVDOC_COMPLETE=bash_source devdoc)"' >> ~/.bashrc
      source ~/.bashrc

    Manual zsh:
      echo 'eval "$(_DEVDOC_COMPLETE=zsh_source devdoc)"' >> ~/.zshrc

    Manual fish:
      echo 'eval (env _DEVDOC_COMPLETE=fish_source devdoc)' >>
      ~/.config/fish/config.fish
    """
    import os

    if shell is None:
        shell_path = os.environ.get("SHELL", "bash")
        if "zsh" in shell_path:
            shell = "zsh"
        elif "fish" in shell_path:
            shell = "fish"
        else:
            shell = "bash"

    if shell == "fish":
        line = "eval (env _DEVDOC_COMPLETE=fish_source devdoc)"
        profile = Path.home() / ".config" / "fish" / "config.fish"
    elif shell == "zsh":
        line = 'eval "$(_DEVDOC_COMPLETE=zsh_source devdoc)"'
        profile = Path.home() / ".zshrc"
    else:
        line = 'eval "$(_DEVDOC_COMPLETE=bash_source devdoc)"'
        profile = Path.home() / ".bashrc"

    if install:
        existing = profile.read_text() if profile.exists() else ""
        if line in existing:
            out.print(f"[yellow]Completion already installed in {profile}[/yellow]")
        else:
            profile.parent.mkdir(parents=True, exist_ok=True)
            with open(profile, "a") as f:
                f.write(f"\n# devdoc shell completion\n{line}\n")
            out.print(f"[green]✓ Completion installed in {profile}[/green]")
            out.print(f"[dim]Reload with:  source {profile}[/dim]")
    else:
        out.print(
            f"[bold]Shell:[/bold] [cyan]{shell}[/cyan]  "
            f"[dim](profile: {profile})[/dim]\n"
        )
        out.print(f"Add this line to [dim]{profile}[/dim]:\n")
        out.print(f"  [green]{line}[/green]\n")
        out.print("Or auto-install with:  [bold]devdoc completion --install[/bold]")


# ---------------------------------------------------------------------------
# devdoc init-mcp  — interactive MCP config wizard
# ---------------------------------------------------------------------------


def _wsl_windows_home() -> Path | None:
    """Return Windows home as a WSL path, or None if not in WSL."""
    try:
        version = Path("/proc/version").read_text().lower()
        if "microsoft" not in version:
            return None
        # Ask Windows for USERPROFILE, then convert the path
        r1 = subprocess.run(
            ["cmd.exe", "/c", "echo %USERPROFILE%"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        win_path = r1.stdout.strip()
        if not win_path or "%" in win_path:
            return None
        r2 = subprocess.run(
            ["wslpath", "-u", win_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        p = r2.stdout.strip()
        return Path(p) if p else None
    except Exception:
        return None


def _make_mcp_entry(devdoc_bin: str) -> dict:
    return {"command": devdoc_bin, "args": ["start"]}


def _json_mcp_install(
    config_path: Path, devdoc_bin: str, top_key: str = "mcpServers"
) -> str:
    """Merge the devdoc MCP entry into a JSON config file. Returns status string."""
    import json as _json

    config_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if config_path.exists():
        try:
            data = _json.loads(config_path.read_text())
        except _json.JSONDecodeError:
            return "error: could not parse existing config"

    servers = data.setdefault(top_key, {})
    already = "devdoc" in servers
    servers["devdoc"] = _make_mcp_entry(devdoc_bin)
    config_path.write_text(_json.dumps(data, indent=2))
    return "updated" if already else "installed"


def _build_client_registry(win_home: Path | None) -> list[dict]:
    """Return the list of known MCP clients with detection info."""
    home = Path.home()

    # Claude Desktop config path — prefer Windows path on WSL
    if win_home:
        claude_desktop_path = (
            win_home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        )
    elif sys.platform == "darwin":
        claude_desktop_path = (
            home
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    else:
        claude_desktop_path = home / ".config" / "Claude" / "claude_desktop_config.json"

    cursor_mcp = (win_home or home) / ".cursor" / "mcp.json"

    return [
        {
            "key": "claude-code",
            "name": "Claude Code",
            "detect": lambda: bool(shutil.which("claude")),
            "method": "cli",
        },
        {
            "key": "claude-desktop",
            "name": "Claude Desktop",
            "detect": lambda p=claude_desktop_path: p.parent.exists(),
            "method": "json",
            "path": claude_desktop_path,
            "json_key": "mcpServers",
        },
        {
            "key": "cursor",
            "name": "Cursor",
            "detect": lambda p=cursor_mcp: p.parent.exists(),
            "method": "json",
            "path": cursor_mcp,
            "json_key": "mcpServers",
        },
        {
            "key": "windsurf",
            "name": "Windsurf",
            "detect": lambda: (home / ".codeium" / "windsurf").exists(),
            "method": "json",
            "path": home / ".codeium" / "windsurf" / "mcp_config.json",
            "json_key": "mcpServers",
        },
        {
            "key": "zed",
            "name": "Zed",
            "detect": lambda: (home / ".config" / "zed").exists(),
            "method": "json",
            "path": home / ".config" / "zed" / "settings.json",
            "json_key": "context_servers",
            "entry_format": "zed",
        },
        {
            "key": "opencode",
            "name": "OpenCode",
            "detect": lambda: bool(shutil.which("opencode")),
            "method": "json",
            "path": home / ".config" / "opencode" / "config.json",
            "json_key": "mcpServers",
        },
        {
            "key": "codex",
            "name": "Codex CLI",
            "detect": lambda: bool(shutil.which("codex")),
            "method": "json",
            "path": home / ".codex" / "config.json",
            "json_key": "mcpServers",
        },
        {
            "key": "kilo",
            "name": "Kilo Code",
            "detect": lambda: bool(shutil.which("kilo")),
            "method": "json",
            "path": home / ".config" / "kilo" / "mcp.json",
            "json_key": "mcpServers",
        },
    ]


@main.command("init-mcp")
@click.option(
    "--all",
    "install_all",
    is_flag=True,
    help="Install for all detected clients without prompting.",
)
def init_mcp(install_all: bool):
    """Interactive wizard to configure devdoc as an MCP server.\n
    Detects installed MCP clients and installs the server config.
    """
    import json as _json

    devdoc_bin = shutil.which("devdoc") or "devdoc"
    win_home = _wsl_windows_home()
    registry = _build_client_registry(win_home)

    if win_home:
        err.print(f"[dim]WSL detected — Windows home: {win_home}[/dim]\n")

    # Detect available clients
    detected = [c for c in registry if c["detect"]()]
    not_found = [c for c in registry if not c["detect"]()]

    if not detected:
        out.print("[yellow]No supported MCP clients detected.[/yellow]")
        out.print("\nSupported clients:")
        for c in registry:
            out.print(f"  [dim]{c['key']:16}[/dim] {c['name']}")
        return

    out.print(f"[bold]Detected {len(detected)} MCP client(s):[/bold]\n")
    for i, c in enumerate(detected, 1):
        out.print(f"  [cyan]{i}.[/cyan] {c['name']}  [dim]({c['key']})[/dim]")

    if not_found:
        missing = ", ".join(c["key"] for c in not_found)
        out.print(f"\n[dim]Not detected ({len(not_found)}): {missing}[/dim]")

    out.print()

    # Select clients
    if install_all:
        targets = detected
    else:
        raw = click.prompt(
            "Install for which clients? (numbers, comma-separated, or 'all')",
            default="all",
        )
        if raw.strip().lower() == "all":
            targets = detected
        else:
            chosen = set()
            for part in raw.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(detected):
                        chosen.add(idx)
                    else:
                        err.print(
                            f"[yellow]  Ignoring invalid selection: {part}[/yellow]"
                        )
            targets = [detected[i] for i in sorted(chosen)]

    if not targets:
        out.print("[yellow]Nothing selected.[/yellow]")
        return

    out.print()

    # Install for each target
    results: list[tuple[str, str, str]] = []
    for client in targets:
        name = client["name"]
        key = client["key"]

        if client["method"] == "cli":
            # Claude Code: use `claude mcp add`
            cmd = [
                "claude",
                "mcp",
                "add",
                "--scope",
                "user",
                "devdoc",
                "--",
                devdoc_bin,
                "start",
            ]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if r.returncode == 0:
                    status = "installed"
                elif "already" in (r.stdout + r.stderr).lower():
                    status = "already configured"
                else:
                    status = f"error: {(r.stderr or r.stdout).strip()[:80]}"
            except FileNotFoundError:
                status = "error: 'claude' binary not found"
            except subprocess.TimeoutExpired:
                status = "error: timed out"

        elif client["method"] == "json":
            entry_format = client.get("entry_format")
            if entry_format == "zed":
                # Zed uses a different schema for context_servers
                cfg_path: Path = client["path"]
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                data = {}
                if cfg_path.exists():
                    try:
                        data = _json.loads(cfg_path.read_text())
                    except _json.JSONDecodeError:
                        status = "error: could not parse zed settings.json"
                        results.append((name, key, status))
                        continue
                servers = data.setdefault("context_servers", {})
                servers["devdoc"] = {
                    "command": {"path": devdoc_bin, "args": ["start"]},
                }
                cfg_path.write_text(_json.dumps(data, indent=2))
                status = "installed"
            else:
                status = _json_mcp_install(
                    client["path"], devdoc_bin, client.get("json_key", "mcpServers")
                )
        else:
            status = "error: unknown method"

        results.append((name, key, status))

    # Summary
    out.print("[bold]Results:[/bold]\n")
    for name, key, status in results:
        if status in ("installed", "updated"):
            out.print(f"  [green]✓[/green] [cyan]{name}[/cyan]  {status}")
        elif "already" in status:
            out.print(f"  [yellow]~[/yellow] [cyan]{name}[/cyan]  {status}")
        else:
            out.print(f"  [red]✗[/red] [cyan]{name}[/cyan]  [red]{status}[/red]")

    out.print(f"\n[dim]MCP server command: {devdoc_bin} start[/dim]")
