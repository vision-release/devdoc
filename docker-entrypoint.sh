#!/bin/sh
set -eu

PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

exec devdoc start --transport sse --host "$HOST" --port "$PORT"
