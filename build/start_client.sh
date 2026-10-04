#!/usr/bin/env sh
set -eu

usage() {
  echo "Usage: build/start_client.sh --id client_num [--sync_folder local_directory] (client_num: integer from 1 to 255)" >&2
  exit 1
}

CLIENT_NUM=""
HOST_PATH=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --id)
      if [ "$#" -lt 2 ] || [ -n "$CLIENT_NUM" ] || [ -z "${2:-}" ]; then
        usage
      fi
      CLIENT_NUM="$2"
      ;;
    --sync_folder)
      if [ "$#" -lt 2 ] || [ -n "$HOST_PATH" ] || [ -z "${2:-}" ]; then
        usage
      fi
      HOST_PATH="$2"
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

SYNC_FOLDER="/app/client/sync_folder"
if [ -n "$HOST_PATH" ]; then
  if [ ! -d "$HOST_PATH" ]; then
    printf 'Sync directory does not exist or is not a directory: %s\n' "$HOST_PATH" >&2
    exit 1
  fi
  case "$HOST_PATH" in
    /*) ;;
    *) HOST_PATH="$PWD/$HOST_PATH" ;;
  esac
  HOST_PATH="$(CDPATH= cd -P "$HOST_PATH" && pwd -P)"
  SYNC_FOLDER="/app/sync_folder"
fi

CLIENT_ID="client${CLIENT_NUM}"
CLIENT_IP="127.127.0.${CLIENT_NUM}"
IMAGE_NAME="pydrop-client"
CONTAINER_NAME="pydrop-client-${CLIENT_NUM}"

set -- "$IMAGE_NAME" \
  python -u -m client.client --client_id "$CLIENT_ID" --bind_ip "$CLIENT_IP"
if [ -n "$HOST_PATH" ]; then
  # Docker parses --mount as CSV, so escape quotes in the source field.
  MOUNT_SOURCE="$(printf '%s' "$HOST_PATH" | sed 's/"/""/g')"
  set -- --mount "type=bind,\"source=$MOUNT_SOURCE\",target=$SYNC_FOLDER" \
    "$@" --sync_folder "$SYNC_FOLDER"
fi

docker build -f build/Dockerfile.client -t "$IMAGE_NAME" .

echo "Starting $CONTAINER_NAME as $CLIENT_ID from $CLIENT_IP, connecting to 127.127.0.0:5001."
echo "Open the sync folder with: build/open_client_sync.sh --id $CLIENT_NUM"
exec docker run --rm -it \
  --name "$CONTAINER_NAME" \
  --network host \
  --label pydrop.role=client \
  --label "pydrop.client_id=$CLIENT_ID" \
  --label "pydrop.sync_folder=$SYNC_FOLDER" \
  "$@"
