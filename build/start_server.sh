#!/usr/bin/env sh
set -eu

IMAGE_NAME="pydrop-server"
CONTAINER_NAME="pydrop-server"
PORT="5001"

docker build -f build/Dockerfile.server -t "$IMAGE_NAME" .

echo "Starting $CONTAINER_NAME on 127.20.0.0:$PORT with host networking. Press Ctrl+C to stop."
exec docker run --rm \
  --name "$CONTAINER_NAME" \
  --network host \
  --label pydrop.role=server \
  -e PYDROP_PORT="$PORT" \
  "$IMAGE_NAME"
