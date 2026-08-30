#!/usr/bin/env sh
set -eu

IMAGE_NAME="pydrop-server"
CONTAINER_NAME="pydrop-server-$(date +%Y%m%d%H%M%S)"
NETWORK_NAME="pydrop-net"
PORT="${PYDROP_PORT:-5001}"

docker build -f build/Dockerfile.server -t "$IMAGE_NAME" .
docker network inspect "$NETWORK_NAME" >/dev/null 2>&1 || docker network create "$NETWORK_NAME" >/dev/null

echo "Starting $CONTAINER_NAME on Docker network port $PORT. Press Ctrl+C to stop."
exec docker run --rm \
  --name "$CONTAINER_NAME" \
  --network "$NETWORK_NAME" \
  --network-alias pydrop-server \
  --label pydrop.role=server \
  -e PYDROP_BIND_HOST=0.0.0.0 \
  -e PYDROP_PORT="$PORT" \
  "$IMAGE_NAME"
