#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build/pyinstaller"
ENTRYPOINT="$ROOT_DIR/scripts/devdoc_entry.py"
OUTPUT_NAME="devdoc-linux-x86_64"

mkdir -p "$DIST_DIR" "$BUILD_DIR"

uvx --from pyinstaller pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name "$OUTPUT_NAME" \
  --distpath "$DIST_DIR" \
  --workpath "$BUILD_DIR" \
  --specpath "$BUILD_DIR" \
  --add-data "$ROOT_DIR/devdoc/knowledge.csv:devdoc" \
  "$ENTRYPOINT"
