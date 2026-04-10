# DevDoc installer — Windows (PowerShell 5.1+ / PowerShell 7+)
# Usage:  .\install.ps1
#         PowerShell -ExecutionPolicy Bypass -File install.ps1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

function Write-Step  { param($msg) Write-Host "[devdoc] $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "  ✓ $msg"      -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  ⚠ $msg"      -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "  ✗ $msg"      -ForegroundColor Red; exit 1 }

# ── 1. Ensure uv is present ────────────────────────────────────────────────
Write-Step "Checking for uv..."

$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Step "uv not found — installing..."
    try {
        # Official uv Windows installer
        $uvInstall = "$env:TEMP\uv-installer.ps1"
        Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $uvInstall
        & PowerShell -ExecutionPolicy Bypass -File $uvInstall
        Remove-Item $uvInstall -Force

        # Refresh PATH for this session
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + $env:PATH

        $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $uvCmd) { Write-Fail "uv install succeeded but 'uv' not found. Restart PowerShell and rerun." }
        Write-Ok "uv installed: $(uv --version)"
    } catch {
        Write-Fail "Failed to install uv: $_`nInstall manually from https://docs.astral.sh/uv/"
    }
} else {
    Write-Ok "uv found: $(uv --version)"
}

# ── 2. Install devdoc ──────────────────────────────────────────────────────
Write-Step "Installing devdoc from $ScriptDir..."
# Pin Python 3.13 — widest pre-built wheel coverage (avoids source builds)
& uv tool install --force --python 3.13 $ScriptDir
if ($LASTEXITCODE -ne 0) { Write-Fail "uv tool install failed." }

# ── 3. Ensure uv tools are on PATH ────────────────────────────────────────
$uvToolBin = & uv tool bin-dir 2>$null
if ($uvToolBin -and (Test-Path $uvToolBin)) {
    $userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$uvToolBin*") {
        Write-Warn "Adding $uvToolBin to your user PATH..."
        [System.Environment]::SetEnvironmentVariable(
            "PATH", "$userPath;$uvToolBin", "User"
        )
        $env:PATH = "$env:PATH;$uvToolBin"
        Write-Warn "PATH updated. Restart PowerShell for it to take effect globally."
    }
    $env:PATH = "$env:PATH;$uvToolBin"
}

# ── 3b. Install Playwright browsers for crawl4ai ─────────────────────────
Write-Step "Installing Playwright browsers (for crawl4ai web crawling)..."
try {
    & uv run --with crawl4ai playwright install chromium --with-deps
    if ($LASTEXITCODE -ne 0) { Write-Warn "Playwright browser install failed. Run manually: playwright install chromium" }
} catch {
    Write-Warn "Could not run playwright install: $_"
}

# ── 4. Verify ──────────────────────────────────────────────────────────────
$devdocCmd = Get-Command devdoc -ErrorAction SilentlyContinue
if ($devdocCmd) {
    Write-Ok "devdoc installed: $(devdoc --version)"
    Write-Host ""
    Write-Host "Quick start:" -ForegroundColor White
    Write-Host "  devdoc add godot https://github.com/godotengine/godot-docs.git"
    Write-Host "  devdoc add godot https://docs.godotengine.org/en/stable/"
    Write-Host "  devdoc list"
    Write-Host "  devdoc start"
    Write-Host ""
    Write-Host "For MCP client config:  devdoc mcp-config" -ForegroundColor Cyan
} else {
    Write-Warn "'devdoc' not found in PATH after install."
    Write-Warn "Restart PowerShell, then run:  devdoc --version"
}
