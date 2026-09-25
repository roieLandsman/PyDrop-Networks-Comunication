from argparse import ArgumentParser
import json
from socket import socket, create_connection
import time
from pathlib import Path
from client.api import requests, responses
from client.constants import *
from client.file_utils import *
from client.manage_folder import Folder
from log import log
from client.protocol import read_message, send_message
from client.validation import validate_client_id, validate_filename

class Client:
    def __init__(self, client_id: str, folder_name: Path = SYNC_FOLDER) -> None:
        validate_client_id(client_id)
        self.client_id = client_id
        self.folder_name = folder_name
        self.server_versions = {}
        self.last_update_check = 0.0
        self.folder = Folder(self.folder_name)
        self.snapshot = self.folder.export()
        self.load_state()
        
        state_file = self.folder_name / STATE_FILE_NAME

    def load_state(self) -> None:
        path = self.state_file
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_data = json.load(f)
            self.snapshot = file_data.get("snapshot", {})
            versions = file_data.get("server_versions", {})
            self.server_versions = {
                name: int(version) for name, version in versions.items()
            }
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            log.error(f"could not load client state: {error}")

    def save_state(self) -> None:
        file_data = {"snapshot": self.snapshot, "server_versions": self.server_versions}
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(file_data, f, indent=4, sort_keys=True)

    def refresh_snapshot(self) -> dict:
        self.folder.refresh()
        return self.folder.get_diff(self.snapshot)

    def has_local_edit(self, filename: str) -> bool:
        self.folder.refresh()
        metadata = self.folder.get_single_file_metadata(filename)
        known_metadata = self.snapshot.get(filename)
        if metadata is None:
            return False
        if known_metadata is None:
            return True
        return metadata.get("hash") != known_metadata.get("hash")

    def has_current_file(self, filename: str) -> bool:
        self.folder.refresh()
        return self.folder.get_single_file_metadata(filename) is not None

    def has_local_remote_conflict(self, filename: str, metadata: dict) -> bool:
        self.folder.refresh()
        local_metadata = self.folder.get_single_file_metadata(filename)
        if local_metadata is None:
            return False
        return local_metadata.get("hash") != metadata.get("hash")

    def remember_version(self, filename: str, version: int) -> None:
        self.server_versions[filename] = int(version)
        self.save_state()

    def remember_synced_file(self, filename: str, metadata: dict, version: int) -> None:
        self.folder.update_single_file_metadata(filename, metadata)
        self.snapshot[filename] = metadata
        self.remember_version(filename, version)

    def remember_synced_delete(self, filename: str, version: int) -> None:
        self.folder.delete_file(filename)
        self.snapshot.pop(filename, None)
        self.remember_version(filename, version)

    def apply_download(self, filename: str, payload: bytes, metadata: dict) -> None:
        write_file(filename, payload, self.folder_name, metadata.get("mtime"))
        self.folder.refresh()
        self.snapshot = self.folder.export()
        self.server_versions[filename] = int(metadata.get("version", 0))
        self.save_state()

    def apply_delete(self, filename: str) -> None:
        delete_file(filename, self.folder_name)
        self.folder.refresh()
        self.snapshot = self.folder.export()
        self.server_versions.pop(filename, None)
        self.save_state()

    def preserve_local_copy(self, filename: str) -> None:
        rename_to_local(filename, self.folder_name)
        self.folder.refresh()
        self.snapshot = self.folder.export()
        self.server_versions.pop(filename, None)
        self.save_state()


def request_response(sock: socket, header: dict, payload: bytes = b"") -> tuple:
    send_message(sock, header, payload)
    server_address = f"{HOST}:{PORT}"
    client_id = header.get("client_id", "unknown")
    log.sent(header.get("action", "UNKNOWN"), 'server', server_address)
    response = read_message(sock)
    if response is None:
        log.error("connection issue: server closed connection")
        raise ConnectionError("server closed connection")
    response_header, _ = response
    log.received(response_header.get("action", "UNKNOWN"), 'server', server_address)
    return response


def ensure_ack(response: tuple) -> tuple:
    header, payload = response
    if header.get("action") == "ERROR":
        log.error(f"server returned error: {header.get('code')}: {header.get('message')}")
        raise RuntimeError(f"{header.get('code')}: {header.get('message')}")
    if header.get("action") != "ACK":
        log.error(f"unexpected server response: {header.get('action')}")
        raise RuntimeError(f"unexpected response: {header.get('action')}")
    return header, payload


def send_connect(sock: socket, client: Client) -> None:
    ensure_ack(request_response(sock, requests.connect(client.client_id)))
    log.info(f"connected as {client.client_id}")


def fetch_server_snapshot(sock: socket, client: Client) -> dict:
    header, payload = ensure_ack(
        request_response(sock, requests.check_updates(client.client_id))
    )
    client.last_update_check = time.monotonic()
    return responses.snapshot(header, payload)


def has_unseen_server_version(client: Client, filename: str, metadata: dict) -> bool:
    server_version = int(metadata.get("version", 0))
    local_version = client.server_versions.get(filename, 0)
    return server_version > local_version


def has_delete_conflict(client: Client, filename: str, metadata: dict) -> bool:
    if not has_unseen_server_version(client, filename, metadata):
        return False
    if client.has_local_edit(filename):
        return True
    return filename not in client.server_versions and client.has_current_file(filename)


def download_one_file(sock: socket, client: Client, filename: str) -> None:
    response = request_response(sock, requests.download(client.client_id, filename))
    header, payload = ensure_ack(response)
    metadata = header.get("metadata", {})
    if metadata.get("hash") != sha256_bytes(payload):
        log.error(f"download hash mismatch: {filename}")
        raise RuntimeError(f"HASH_MISMATCH: {filename}")
    client.apply_download(filename, payload, metadata)
    log.info(f"downloaded: {filename}")


def has_upload_conflict(sock: socket, client: Client, filename: str) -> bool:
    snapshot = fetch_server_snapshot(sock, client)
    metadata = snapshot["files"].get(filename)
    deleted_metadata = snapshot["deleted"].get(filename)
    if deleted_metadata is not None and has_delete_conflict(
        client, filename, deleted_metadata
    ):
        client.preserve_local_copy(filename)
        log.info(f"kept local conflict as {filename}.local")
        return True
    if metadata is None:
        return False
    if not client.has_local_edit(filename):
        return False
    if not has_unseen_server_version(client, filename, metadata):
        return False
    client.preserve_local_copy(filename)
    download_one_file(sock, client, filename)
    log.info(f"kept local conflict as {filename}.local")
    return True


def build_file_request(client: Client, action: str, metadata: dict) -> dict:
    if action == "UPLOAD":
        return requests.upload(
            client.client_id,
            metadata["filename"],
            metadata["size"],
            metadata["mtime"],
            metadata["hash"],
        )
    version = client.server_versions.get(metadata["filename"])
    return requests.update(
        client.client_id,
        metadata["filename"],
        metadata["size"],
        metadata["mtime"],
        metadata["hash"],
        version,
    )


def send_file_change(sock: socket, client: Client, action: str, filename: str) -> None:
    metadata = client.folder.get_single_file_metadata(filename)
    if metadata is None:
        return
    if has_upload_conflict(sock, client, filename):
        return
    payload = read_file(filename, client.folder.path)
    header = build_file_request(client, action, metadata)
    try:
        response_header, _ = ensure_ack(request_response(sock, header, payload))
    except RuntimeError as error:
        if not str(error).startswith("STALE_VERSION"):
            log.error(f"{action.lower()} failed for {filename}: {error}")
            raise
        if has_upload_conflict(sock, client, filename):
            return
        log.error(f"{action.lower()} rejected as stale for {filename}: {error}")
        raise
    response_metadata = response_header.get("metadata", {})
    client.remember_synced_file(filename, metadata, response_metadata.get("version", 0))
    log.info(f"{action.lower()} accepted: {filename}")


def send_delete(sock: socket, client: Client, filename: str) -> None:
    version = client.server_versions.get(filename, 0)
    try:
        header = requests.delete(client.client_id, filename, version)
        response = request_response(sock, header)
        response_header, _ = ensure_ack(response)
    except RuntimeError as error:
        if not str(error).startswith("STALE_VERSION"):
            raise
        log.error(f"delete rejected as stale for {filename}: {error}")
        check_remote_updates(sock, client)
        return
    response_metadata = response_header.get("metadata", {})
    client.remember_synced_delete(filename, response_metadata.get("version", 0))
    log.info(f"delete accepted: {filename}")


def send_local_changes(sock: socket, client: Client) -> None:
    changes = client.refresh_snapshot()
    for filename in changes["added"]:
        send_file_change(sock, client, "UPLOAD", filename)
    for filename in changes["modified"]:
        send_file_change(sock, client, "UPDATE", filename)
    for filename in changes["deleted"]:
        send_delete(sock, client, filename)


def should_check_updates(client: Client) -> bool:
    return time.monotonic() - client.last_update_check >= UPDATE_INTERVAL_SECONDS


def upload_local_only_files(sock: socket, client: Client, remote_files: dict) -> None:
    local_names = sorted(client.snapshot)
    for filename in local_names:
        if filename not in remote_files:
            send_file_change(sock, client, "UPLOAD", filename)


def preserve_download_conflict(client: Client, filename: str, metadata: dict) -> None:
    if not has_unseen_server_version(client, filename, metadata):
        return
    is_fresh_conflict = filename not in client.server_versions
    if client.has_local_edit(filename) or (
        is_fresh_conflict and client.has_local_remote_conflict(filename, metadata)
    ):
        client.preserve_local_copy(filename)
        log.info(f"kept local conflict as {filename}.local")


def is_current_file(client: Client, filename: str, metadata: dict) -> bool:
    version = int(metadata.get("version", 0))
    local_metadata = client.snapshot.get(filename)
    if local_metadata is None:
        return False
    if local_metadata.get("hash") == metadata.get("hash"):
        client.remember_version(filename, version)
        return True
    return client.server_versions.get(filename, 0) >= version


def download_changed_files(sock: socket, client: Client, files: dict) -> None:
    for filename, metadata in sorted(files.items()):
        try:
            validate_filename(filename)
        except ValueError:
            log.error(f"skipped invalid remote filename: {filename}")
            continue
        if is_current_file(client, filename, metadata):
            continue
        preserve_download_conflict(client, filename, metadata)
        download_one_file(sock, client, filename)


def mark_remote_deletions(sock: socket, client: Client, deleted: dict) -> None:
    filenames = []
    for filename, metadata in sorted(deleted.items()):
        try:
            validate_filename(filename)
        except ValueError:
            log.error(f"skipped invalid remote filename: {filename}")
            continue
        if metadata.get("origin_client") == client.client_id:
            continue
        if has_delete_conflict(client, filename, metadata):
            client.preserve_local_copy(filename)
            log.info(f"kept local conflict as {filename}.local")
        client.apply_delete(filename)
        filenames.append(filename)
        log.info(f"deleted remotely: {filename}")
    if filenames:
        response = request_response(sock, requests.delete_seen(client.client_id, filenames))
        ensure_ack(response)


def check_remote_updates(sock: socket, client: Client) -> dict:
    snapshot = fetch_server_snapshot(sock, client)
    download_changed_files(sock, client, snapshot["files"])
    mark_remote_deletions(sock, client, snapshot["deleted"])
    return snapshot


def initial_reconcile(sock: socket, client: Client) -> None:
    send_local_changes(sock, client)
    snapshot = check_remote_updates(sock, client)
    upload_local_only_files(sock, client, snapshot["files"])


def run_connected_loop(sock: socket, client: Client) -> None:
    while True:
        send_local_changes(sock, client)
        if should_check_updates(client):
            check_remote_updates(sock, client)
        time.sleep(SCAN_INTERVAL_SECONDS)


def sync_with_server(client: Client) -> None:
    log.info(f"watching folder {client.folder}")
    while True:
        try:
            log.info(f"connecting to {HOST}:{PORT}")
            with create_connection((HOST, PORT)) as sock:
                send_connect(sock, client)
                initial_reconcile(sock, client)
                run_connected_loop(sock, client)
        except (OSError, RuntimeError, ConnectionError, ValueError) as error:
            log.error(f"connection issue: {error}")
            time.sleep(RECONNECT_DELAY_SECONDS)


def main() -> None:
    parser = ArgumentParser(description="Run a PyDrop client")
    parser.add_argument("--client_id")
    parser.add_argument("--sync_folder", default=SYNC_FOLDER, type=Path)
    args = parser.parse_args()

    try:
        sync_with_server(Client(args.client_id, args.sync_folder))
    except KeyboardInterrupt:
        log.info("stopped by user")

if __name__ == "__main__":
    main()
