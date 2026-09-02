"""PyDrop client entry point."""

import argparse
import socket
import time

from client.api import requests, responses
from client.constants import HOST, PORT, RECONNECT_DELAY_SECONDS, SCAN_INTERVAL_SECONDS
from client.constants import SYNC_FOLDER, UPDATE_INTERVAL_SECONDS
from client.file_utils import read_file, sha256_bytes
from client.protocol import read_message, send_message
from client.state import ClientState


def log(message: str) -> None:
    """Print one client log line immediately."""
    print(f"[client] {message}", flush=True)


def request_response(sock: socket.socket, header: dict, payload: bytes = b"") -> tuple:
    """Send one request and return one response."""
    send_message(sock, header, payload)
    response = read_message(sock)
    if response is None:
        raise ConnectionError("server closed connection")
    return response


def ensure_ack(response: tuple) -> tuple:
    """Return response header or raise for server ERROR."""
    header, payload = response
    if header.get("action") == "ERROR":
        raise RuntimeError(f"{header.get('code')}: {header.get('message')}")
    if header.get("action") != "ACK":
        raise RuntimeError(f"unexpected response: {header.get('action')}")
    return header, payload
def send_connect(sock: socket.socket, state: ClientState) -> None:
    """Register this client with the server."""
    response = request_response(sock, requests.connect(state.client_id))
    ensure_ack(response)
    log(f"connected as {state.client_id}")
def send_file_change(
    sock: socket.socket, state: ClientState, action: str, filename: str
) -> None:
    """Upload a new or modified file to the server."""
    metadata = state.current_metadata(filename)
    if metadata is None:
        return
    payload = read_file(filename, state.folder)
    header = build_file_request(state, action, metadata)
    response_header, _ = ensure_ack(request_response(sock, header, payload))
    response_metadata = response_header.get("metadata", {})
    state.remember_synced_file(filename, metadata, response_metadata.get("version", 0))
    log(f"{action.lower()} accepted: {filename}")

def build_file_request(state: ClientState, action: str, metadata: dict) -> dict:
    """Build an UPLOAD or UPDATE request from file metadata."""
    if action == "UPLOAD":
        return requests.upload(
            state.client_id,
            metadata["filename"],
            metadata["size"],
            metadata["mtime"],
            metadata["hash"],
        )
    version = state.server_versions.get(metadata["filename"])
    return requests.update(
        state.client_id,
        metadata["filename"],
        metadata["size"],
        metadata["mtime"],
        metadata["hash"],
        version,
    )

def send_delete(sock: socket.socket, state: ClientState, filename: str) -> None:
    """Send a local delete request to the server."""
    response_header, _ = ensure_ack(
        request_response(sock, requests.delete(state.client_id, filename))
    )
    response_metadata = response_header.get("metadata", {})
    state.remember_synced_delete(filename, response_metadata.get("version", 0))
    log(f"delete accepted: {filename}")

def send_local_changes(sock: socket.socket, state: ClientState) -> None:
    """Send local added, modified, and deleted files."""
    changes = state.refresh_snapshot()
    for filename in changes["added"]:
        send_file_change(sock, state, "UPLOAD", filename)
    for filename in changes["modified"]:
        send_file_change(sock, state, "UPDATE", filename)
    for filename in changes["deleted"]:
        send_delete(sock, state, filename)

def should_check_updates(state: ClientState) -> bool:
    """Return True when it is time to ask for server updates."""
    return time.monotonic() - state.last_update_check >= UPDATE_INTERVAL_SECONDS

def check_remote_updates(sock: socket.socket, state: ClientState) -> dict:
    """Download changed remote files and apply remote deletions."""
    header, payload = ensure_ack(
        request_response(sock, requests.check_updates(state.client_id))
    )
    state.last_update_check = time.monotonic()
    snapshot = responses.snapshot(header, payload)
    download_changed_files(sock, state, snapshot["files"])
    mark_remote_deletions(sock, state, snapshot["deleted"])
    return snapshot

def initial_reconcile(sock: socket.socket, state: ClientState) -> None:
    """Load local files, apply server files, then upload local-only files."""
    state.load_snapshot()
    snapshot = check_remote_updates(sock, state)
    upload_local_only_files(sock, state, snapshot["files"])

def upload_local_only_files(
    sock: socket.socket, state: ClientState, remote_files: dict
) -> None:
    """Upload startup files that are absent from the server snapshot."""
    local_names = sorted(state.snapshot)
    for filename in local_names:
        if filename not in remote_files:
            send_file_change(sock, state, "UPLOAD", filename)

def download_changed_files(sock: socket.socket, state: ClientState, files: dict) -> None:
    """Download remote files whose server version is newer."""
    for filename, metadata in sorted(files.items()):
        if is_current_file(state, filename, metadata):
            continue
        download_one_file(sock, state, filename)

def is_current_file(state: ClientState, filename: str, metadata: dict) -> bool:
    """Return True when the local file already matches the server file."""
    version = int(metadata.get("version", 0))
    local_metadata = state.snapshot.get(filename)
    if local_metadata is None:
        return False
    if local_metadata.get("hash") == metadata.get("hash"):
        state.remember_version(filename, version)
        return True
    return state.server_versions.get(filename, 0) >= version

def download_one_file(sock: socket.socket, state: ClientState, filename: str) -> None:
    """Download one server file and write it locally."""
    response = request_response(sock, requests.download(state.client_id, filename))
    header, payload = ensure_ack(response)
    metadata = header.get("metadata", {})
    if metadata.get("hash") != sha256_bytes(payload):
        raise RuntimeError(f"HASH_MISMATCH: {filename}")
    state.apply_download(filename, payload, metadata)
    log(f"downloaded: {filename}")

def mark_remote_deletions(sock: socket.socket, state: ClientState, deleted: dict) -> None:
    """Apply remote tombstones and acknowledge them."""
    filenames = []
    for filename, metadata in sorted(deleted.items()):
        if metadata.get("origin_client") == state.client_id:
            continue
        state.apply_delete(filename)
        filenames.append(filename)
        log(f"deleted remotely: {filename}")
    if filenames:
        response = request_response(sock, requests.delete_seen(state.client_id, filenames))
        ensure_ack(response)

def sync_forever(state: ClientState, host: str, port: int) -> None:
    """Run the reconnecting client synchronization loop."""
    log(f"watching folder {state.folder}")
    while True:
        try:
            log(f"connecting to {host}:{port}")
            with socket.create_connection((host, port)) as sock:
                send_connect(sock, state)
                initial_reconcile(sock, state)
                run_connected_loop(sock, state)
        except (OSError, RuntimeError, ConnectionError, ValueError) as error:
            log(f"connection issue: {error}")
            time.sleep(RECONNECT_DELAY_SECONDS)

def run_connected_loop(sock: socket.socket, state: ClientState) -> None:
    """Run sync work while connected to the server."""
    while True:
        send_local_changes(sock, state)
        if should_check_updates(state):
            check_remote_updates(sock, state)
        time.sleep(SCAN_INTERVAL_SECONDS)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run a PyDrop client")
    parser.add_argument("--client-id", default="client-local")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", default=PORT, type=int)
    parser.add_argument("--folder", default=SYNC_FOLDER)
    return parser.parse_args()

def main() -> None:
    """Run the PyDrop client from the command line."""
    args = parse_args()
    state = ClientState(args.client_id, args.folder)
    sync_forever(state, args.host, args.port)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("stopped")
