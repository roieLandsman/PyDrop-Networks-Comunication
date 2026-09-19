#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: build/start_client.sh client_id" >&2
  exit 1
fi

CLIENT_ID="$1"
IMAGE_NAME="pydrop-client"
CONTAINER_NAME="pydrop-client-$CLIENT_ID-$(date +%Y%m%d%H%M%S)"
NETWORK_NAME="pydrop-net"

docker build -f build/Dockerfile.client -t "$IMAGE_NAME" .
docker network inspect "$NETWORK_NAME" >/dev/null 2>&1 || docker network create "$NETWORK_NAME" >/dev/null

echo "Starting $CONTAINER_NAME."
echo "Open the sync folder with: build/open_client_sync.sh $CLIENT_ID"
exec docker run --rm -it \
  --name "$CONTAINER_NAME" \
  --network "$NETWORK_NAME" \
  --label pydrop.role=client \
  --label "pydrop.client_id=$CLIENT_ID" \
  "$IMAGE_NAME" \
  python -u -m client.client --client_id "$CLIENT_ID"
