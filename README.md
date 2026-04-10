# DevDoc — Documentation MCP Service

A CLI tool that crawls documentation (websites or Git repositories), saves it as Markdown, and exposes it as an **MCP (Model Context Protocol) server** for local LLMs and AI agents.

---

## What You Can Do

With DevDoc, you can:

1. Add public documentation from websites or Git repositories
2. Use a built-in knowledge base of common docs without looking up URLs yourself
3. Keep documentation cached locally for fast offline searching
4. Search docs from the terminal before connecting any MCP client
5. Run an MCP server for local AI tools over `stdio`
6. Run an HTTP/SSE MCP server for agents and remote tooling
7. Start the service in Docker with a single startup script
8. Update, inspect, and remove documentation sources at any time

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
uv tool install --python 3.13 /path/to/devdoc
```

---

## Quick Start

### Local CLI

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

### Docker

```bash
./start-docker.sh
```

This builds the image, starts the container, and exposes the SSE endpoint on `http://localhost:8080/sse`.

Use a different port if needed:

```bash
./start-docker.sh 9090
```

---

## All Commands

### Command Summary

| Command | What it does |
|---------|--------------|
| `devdoc kb` | Browse built-in documentation sources |
| `devdoc add` | Add and download a documentation source |
| `devdoc list` | List all configured sources |
| `devdoc status` | Show health and environment details |
| `devdoc info` | Inspect one source in detail |
| `devdoc update` | Refresh one or all sources |
| `devdoc remove` / `devdoc rm` | Delete a source |
| `devdoc search` | Search local docs from the terminal |
| `devdoc start` | Run the MCP server |
| `devdoc stop` | Stop the background SSE daemon |
| `devdoc logs` | View daemon logs |
| `devdoc mcp-config` | Print MCP client configuration |
| `devdoc init-mcp` | Attempt to configure supported MCP clients |

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

### Docker startup

Build and start the Docker container with the included startup script:

```bash
./start-docker.sh
```

Use a different port by passing it as the first argument:

```bash
./start-docker.sh 9090
```

The script:
1. Builds the local Docker image
2. Starts the container in SSE mode
3. Maps the selected port to the same port in the container
4. Persists DevDoc data in the Docker volume `devdoc-data`

The container entrypoint uses `PORT` and defaults to `8080`.

You can also override names with environment variables:

```bash
IMAGE_NAME=my-devdoc CONTAINER_NAME=my-devdoc DATA_VOLUME=my-devdoc-data ./start-docker.sh
```

Useful Docker commands:

```bash
docker ps
docker logs -f devdoc
docker stop devdoc
docker start devdoc
docker rm -f devdoc
docker volume ls
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

## Typical Workflows

### 1. Add docs and search locally

```bash
devdoc add python
devdoc search "asyncio gather"
```

### 2. Add a custom documentation site

```bash
devdoc add mylib https://docs.example.com/
devdoc search "authentication token" -s mylib
```

### 3. Run for a desktop MCP client

```bash
devdoc start
```

Then generate client configuration:

```bash
devdoc mcp-config
```

### 4. Run as a networked SSE service

```bash
devdoc start --transport sse --host 0.0.0.0 --port 8080
```

### 5. Run in the background

```bash
devdoc start --transport sse --daemon
devdoc logs
devdoc stop
```

### 6. Run in Docker

```bash
./start-docker.sh
docker logs -f devdoc
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

## Notes

- `stdio` mode is intended for local MCP clients such as Claude Desktop or LM Studio.
- `sse` mode is intended for tools that connect over HTTP.
- Web crawling may require Playwright browser installation.
- Git sources work best when `git` is installed locally.
- Docker mode persists DevDoc data in a named Docker volume, so your source list and downloaded docs survive container replacement.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `devdoc: command not found` | `export PATH="$HOME/.local/bin:$PATH"` then restart shell |
| `lxml build failed` | Use `--python 3.13` (pre-built wheels available) |
| Web crawl returns 0 pages | Run `playwright install chromium` manually |
| Git clone fails | Check git is installed and the URL is correct |
| RST files not converted | Install `pandoc` for best results; built-in fallback handles common cases |
