#!/usr/bin/env bash
# DevDoc installer — Linux / macOS / WSL
# Usage:  bash install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'

log()  { echo -e "${BOLD}[devdoc]${RESET} $*"; }
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $*"; }
fail() { echo -e "${RED}✗${RESET}  $*" >&2; exit 1; }

# ── 1. Ensure uv is present ────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    log "uv not found — installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to current session PATH
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        fail "uv installation failed. Install manually: https://docs.astral.sh/uv/"
    fi
    ok "uv installed: $(uv --version)"
else
    ok "uv found: $(uv --version)"
fi

# ── 2. Install devdoc as a uv tool ────────────────────────────────────────
# Pin Python 3.13 — widest pre-built wheel coverage (avoids source builds)
log "Installing devdoc from ${REPO_DIR}..."
uv cache clean devdoc 2>/dev/null || true   # evict stale cached wheel
uv tool install --force --python 3.13 "$REPO_DIR"

# ── 3. Ensure ~/.local/bin is in PATH ─────────────────────────────────────
UV_BIN="$(uv tool dir)/../../bin"
TOOL_BIN="$HOME/.local/bin"

add_to_path() {
    local shell_rc="$1"
    local export_line='export PATH="$HOME/.local/bin:$PATH"'
    if [[ -f "$shell_rc" ]] && ! grep -qF "$HOME/.local/bin" "$shell_rc"; then
        echo "" >> "$shell_rc"
        echo "# devdoc — added by installer" >> "$shell_rc"
        echo "$export_line" >> "$shell_rc"
        warn "Added PATH entry to ${shell_rc}. Run: source ${shell_rc}"
    fi
}

if ! command -v devdoc &>/dev/null; then
    add_to_path "$HOME/.bashrc"
    add_to_path "$HOME/.zshrc"
    export PATH="$TOOL_BIN:$PATH"
fi

# ── 3b. Install Playwright browsers for crawl4ai ──────────────────────────
log "Installing Playwright browsers (needed for crawl4ai)..."
uv run --with crawl4ai playwright install chromium --with-deps 2>/dev/null || \
    warn "Playwright browser install failed — web crawling may not work. Run manually: playwright install chromium"

# ── 4. Verify ──────────────────────────────────────────────────────────────
if command -v devdoc &>/dev/null; then
    ok "devdoc installed: $(devdoc --version)"
    echo ""
    echo -e "${BOLD}Quick start:${RESET}"
    echo "  devdoc add godot https://github.com/godotengine/godot-docs.git"
    echo "  devdoc add godot https://docs.godotengine.org/en/stable/"
    echo "  devdoc list"
    echo "  devdoc start"
    echo ""
    echo -e "For MCP client config:  ${BOLD}devdoc mcp-config${RESET}"
else
    warn "devdoc binary not found in PATH."
    warn "Try:  export PATH=\"\$HOME/.local/bin:\$PATH\""
    warn "Then: devdoc --version"
fi
