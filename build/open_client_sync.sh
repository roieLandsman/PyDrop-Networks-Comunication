#!/usr/bin/env sh
set -eu

CLIENT_ID="${1:-client1}"
CONTAINER_NAME="$(docker ps \
  --filter label=pydrop.role=client \
  --filter "label=pydrop.client_id=$CLIENT_ID" \
  --format '{{.Names}}' | head -n 1)"
SYNC_FOLDER="/app/client/sync_folder"

if [ -z "$CONTAINER_NAME" ]; then
  echo "No running PyDrop client container found for client id: $CLIENT_ID" >&2
  exit 1
fi

echo "Opening $SYNC_FOLDER inside $CONTAINER_NAME."
exec docker exec -it "$CONTAINER_NAME" sh -lc "mkdir -p '$SYNC_FOLDER' && cd '$SYNC_FOLDER' && exec sh"
