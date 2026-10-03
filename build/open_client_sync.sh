#!/usr/bin/env sh
set -eu

usage() {
  echo "Usage: build/open_client_sync.sh --id client_num (client_num: integer from 1 to 255)" >&2
  exit 1
}

CLIENT_NUM=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --id)
      if [ "$#" -lt 2 ] || [ -n "$CLIENT_NUM" ] || [ -z "${2:-}" ]; then
        usage
      fi
      CLIENT_NUM="$2"
      ;;
    *) usage ;;
  esac
  shift 2
done

case "$CLIENT_NUM" in
  ''|*[!0-9]*) usage ;;
esac

CLIENT_NUM="$(printf '%s' "$CLIENT_NUM" | sed 's/^0*//')"
if [ -z "$CLIENT_NUM" ] || [ "${#CLIENT_NUM}" -gt 3 ] || [ "$CLIENT_NUM" -gt 255 ]; then
  usage
fi

CLIENT_ID="client${CLIENT_NUM}"
CONTAINER_NAME="$(docker ps \
  --filter label=pydrop.role=client \
  --filter "label=pydrop.client_id=$CLIENT_ID" \
  --format '{{.Names}}' | head -n 1)"

if [ -z "$CONTAINER_NAME" ]; then
  echo "No running PyDrop client container found for client id: $CLIENT_ID" >&2
  exit 1
fi

SYNC_FOLDER="$(docker inspect \
  --format '{{with index .Config.Labels "pydrop.sync_folder"}}{{.}}{{end}}' \
  "$CONTAINER_NAME")"
SYNC_FOLDER="${SYNC_FOLDER:-/app/client/sync_folder}"

echo "Opening $SYNC_FOLDER inside $CONTAINER_NAME."
exec docker exec -it "$CONTAINER_NAME" sh -lc 'mkdir -p "$1" && cd "$1" && exec sh' sh "$SYNC_FOLDER"
