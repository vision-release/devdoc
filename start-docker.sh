#!/bin/sh
set -eu

IMAGE_NAME="${IMAGE_NAME:-devdoc}"
CONTAINER_NAME="${CONTAINER_NAME:-devdoc}"
PORT="${1:-${PORT:-8080}}"
DATA_VOLUME="${DATA_VOLUME:-devdoc-data}"

echo "Building Docker image: ${IMAGE_NAME}"
docker build -t "${IMAGE_NAME}" .

if docker ps -a --format '{{.Names}}' | grep -Fx "${CONTAINER_NAME}" >/dev/null 2>&1; then
  echo "Replacing existing container: ${CONTAINER_NAME}"
  docker rm -f "${CONTAINER_NAME}" >/dev/null
fi

echo "Starting ${CONTAINER_NAME} on port ${PORT}"
docker run -d \
  --name "${CONTAINER_NAME}" \
  -e PORT="${PORT}" \
  -p "${PORT}:${PORT}" \
  -v "${DATA_VOLUME}:/root/.devdoc" \
  "${IMAGE_NAME}"

echo "DevDoc is available at http://localhost:${PORT}/sse"
