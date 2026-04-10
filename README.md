# DevDoc — Documentation MCP Service

A CLI tool that crawls documentation (websites or Git repositories), saves it as Markdown, and exposes it as an **MCP (Model Context Protocol) server** for local LLMs and AI agents.

---

## Requirements

| Tool | Notes |
|------|-------|
| [uv](https://docs.astral.sh/uv/) | Python package manager — installed automatically by the installers |
| Git | Only needed when adding `git` sources |
| pandoc _(optional)_ | RST → Markdown conversion for Git repos; falls back to built-in converter |

---

## Installation

### Linux / macOS / WSL

```bash
bash install.sh
```

The script:
1. Installs **uv** if missing
2. Runs `uv tool install --python 3.13 .` → creates the `devdoc` binary at `~/.local/bin/devdoc`
3. Installs **Playwright** (Chromium) for `crawl4ai` web crawling
4. Updates `~/.bashrc` / `~/.zshrc` if `~/.local/bin` is not yet in `PATH`

### Windows (PowerShell)

```powershell
Set-ExecutionPolicy Bypass -Scope Process
.\install.ps1
```

The script:
1. Installs **uv** via the official Windows installer if missing
2. Runs `uv tool install --python 3.13 .` → creates `devdoc.exe`
3. Adds the uv tools directory to your user `PATH`
4. Installs **Playwright** (Chromium)

### Manual (any platform)

```bash
uv tool install --python 3.13 /path/to/godot-docs
```

---

## Quick Start

```bash
# Add from the built-in knowledge base (no URL needed):
devdoc add godot
devdoc add roblox
devdoc add react

# OR supply a custom URL:
devdoc add godot https://github.com/godotengine/godot-docs.git
devdoc add mylib https://docs.example.com/

# Start the MCP server:
devdoc start
```

---

## All Commands

### `devdoc kb [query] [-c category]`

Browse the built-in knowledge base of curated public documentation sources.

```bash
devdoc kb                    # list all (~40 entries grouped by category)
devdoc kb godot              # search by keyword
devdoc kb -c gamedev         # filter by category
devdoc kb -c frontend
devdoc kb -c backend
```

**Categories:** `gamedev`, `frontend`, `backend`, `language`, `graphics`, `mobile`, `desktop`, `testing`, `api`, `web`

**Built-in sources include:**

| Key | Name | Type |
|-----|------|------|
| `godot` | Godot Engine | git |
| `roblox` | Roblox Studio | web |
| `unity` | Unity | web |
| `unreal` | Unreal Engine | web |
| `bevy` | Bevy (Rust) | web |
| `pygame` | Pygame | web |
| `react` | React | web |
| `nextjs` | Next.js | web |
| `vue` | Vue.js | git |
| `nuxt` | Nuxt | web |
| `svelte` | Svelte | web |
| `astro` | Astro | git |
| `solidjs` | SolidJS | web |
| `tailwind` | Tailwind CSS | web |
| `htmx` | HTMX | web |
| `threejs` | Three.js | web |
| `pinia` | Pinia | web |
| `nodejs` | Node.js | web |
| `deno` | Deno | git |
| `bun` | Bun | web |
| `express` | Express | web |
| `fastapi` | FastAPI | web |
| `django` | Django | web |
| `laravel` | Laravel | git |
| `supabase` | Supabase | web |
| `prisma` | Prisma | web |
| `graphql` | GraphQL | web |
| `trpc` | tRPC | web |
| `typescript` | TypeScript | web |
| `python` | Python | web |
| `rust` | Rust (book) | git |
| `go` | Go | web |
| `kotlin` | Kotlin | web |
| `swift` | Swift | web |
| `elixir` | Elixir | web |
| `mdn` | MDN Web Docs | web |
| `flutter` | Flutter | web |
| `tauri` | Tauri | web |
| `electron` | Electron | web |
| `vitest` | Vitest | web |
| `pytest` | pytest | web |

---

### `devdoc add <name> [url]`

Download and index a documentation source. **URL is optional** — if omitted, `name` is looked up in the knowledge base and fails with suggestions if not found.

```bash
# From knowledge base (recommended):
devdoc add godot
devdoc add roblox
devdoc add deno

# Custom URL (auto-detects git vs web):
devdoc add godot   https://github.com/godotengine/godot-docs.git
devdoc add mylib   https://docs.example.com/

# Options:
devdoc add <name> [url] --max-pages 200   # limit crawl size (default: 500)
devdoc add <name> [url] --delay 1.0       # seconds between requests (default: 0.5)
devdoc add <name> [url] --type web        # force source type
```

Downloaded files are stored in `~/.devdoc/docs/<name>/`.

---

### `devdoc list`

Show all configured sources with full details — type, document count, disk size, dates, and URL.

```
┏━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Name   ┃ Type ┃ Docs ┃ Size  ┃ Added      ┃ Updated    ┃ URL           ┃
┡━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ godot  │ git  │ 1842 │ 18 MB │ 2025-03-01 │ 2025-03-01 │ github.com/…  │
└────────┴──────┴──────┴───────┴────────────┴────────────┴───────────────┘
```

---

### `devdoc status`

Overall health check — binary path, config location, totals across all sources, and per-source state (including Git branch/commit for git sources).

```bash
devdoc status
```

---

### `devdoc info <name>`

Detailed panel for a single source: metadata, file counts, disk size, Git branch + last commit, and top-level directory structure.

```bash
devdoc info godot
```

---

### `devdoc update [name]`

Re-crawl (git pull / re-crawl website) to refresh documentation. Omit `name` to update all sources.

```bash
devdoc update          # update everything
devdoc update godot    # update one source
```

---

### `devdoc remove <name>` / `devdoc rm <name>`

Delete a source from the config and remove all downloaded files.

```bash
devdoc remove godot
devdoc rm godot        # short alias
devdoc rm godot --yes  # skip confirmation prompt
```

---

### `devdoc search <query>`

Search documentation locally — useful for testing without an MCP client.

```bash
devdoc search "signals and slots"
devdoc search "AnimationPlayer" -s godot   # limit to one source
devdoc search "coroutine" -n 5             # top 5 results
```

---

### `devdoc start`

Start the MCP server. All configured sources are available as tools.

```bash
# stdio transport (default) — for Claude Desktop, LM Studio, etc.
devdoc start

# HTTP/SSE transport — for agents that connect via HTTP
devdoc start --transport sse --port 8080 --host 0.0.0.0
```

---

### `devdoc mcp-config`

Print the JSON snippet to paste into your MCP client config (e.g. Claude Desktop `claude_desktop_config.json`).

```bash
devdoc mcp-config              # stdio (default)
devdoc mcp-config --transport sse --port 8080
```

Example output:
```json
{
  "mcpServers": {
    "devdoc": {
      "command": "/home/user/.local/bin/devdoc",
      "args": ["start"]
    }
  }
}
```

---

## MCP Tools (available to connected LLMs/agents)

| Tool | Description |
|------|-------------|
| `list_sources` | List all configured doc sources with counts |
| `search_docs(query, source?)` | Keyword search across all docs, returns top 10 with snippets |
| `get_document(path)` | Full content of a file (path from search results) |
| `list_documents(source, path?)` | Browse files in a source by sub-path |

### Example agent workflow

```
list_sources()
→ "godot (git) — 1842 docs"

search_docs("AnimationPlayer track methods")
→ 1. AnimationPlayer  classes/class_animationplayer.md
     …adds a new track to the animation…

get_document("godot/classes/class_animationplayer.md")
→ Full class reference
```

---

## Storage Layout

```
~/.devdoc/
├── sources.json            # source registry
└── docs/
    ├── godot/              # git clone or crawled pages
    │   ├── .git/
    │   ├── tutorials/
    │   ├── classes/
    │   │   ├── class_node.md
    │   │   └── …
    │   └── …
    └── python/
        └── …
```

---

## Updating devdoc itself

```bash
# From the project directory:
uv tool install --reinstall --python 3.13 .
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `devdoc: command not found` | `export PATH="$HOME/.local/bin:$PATH"` then restart shell |
| `lxml build failed` | Use `--python 3.13` (pre-built wheels available) |
| Web crawl returns 0 pages | Run `playwright install chromium` manually |
| Git clone fails | Check git is installed and the URL is correct |
| RST files not converted | Install `pandoc` for best results; built-in fallback handles common cases |
