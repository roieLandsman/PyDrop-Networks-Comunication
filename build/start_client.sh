#!/usr/bin/env sh
set -eu

CLIENT_ID="${1:-client1}"
IMAGE_NAME="pydrop-client"
CONTAINER_NAME="pydrop-client-$CLIENT_ID-$(date +%Y%m%d%H%M%S)"
NETWORK_NAME="pydrop-net"
PORT="${PYDROP_PORT:-5001}"
SERVER_HOST="${PYDROP_SERVER_HOST:-pydrop-server}"

docker build -f build/Dockerfile.client -t "$IMAGE_NAME" .
docker network inspect "$NETWORK_NAME" >/dev/null 2>&1 || docker network create "$NETWORK_NAME" >/dev/null

echo "Starting $CONTAINER_NAME and connecting to $SERVER_HOST:$PORT."
echo "Open the sync folder with: build/open_client_sync.sh $CLIENT_ID"
exec docker run --rm -it \
  --name "$CONTAINER_NAME" \
  --network "$NETWORK_NAME" \
  --label pydrop.role=client \
  --label "pydrop.client_id=$CLIENT_ID" \
  -e PYDROP_SERVER_HOST="$SERVER_HOST" \
  -e PYDROP_PORT="$PORT" \
  "$IMAGE_NAME" \
  python -u -m client.client \
    --client-id "$CLIENT_ID" \
    --host "$SERVER_HOST" \
    --port "$PORT"
