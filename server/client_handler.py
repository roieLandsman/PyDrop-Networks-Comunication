"""Per-client server-side request handling for PyDrop."""

import threading
from server.constants import ERROR_UNKNOWN_ACTION, ERROR_BAD_REQUEST
from server.protocol import read_message, send_message, error
from server.file_utils import (
    load_metadata,
    clean_filename,
    write_file,
    build_file_metadata,
    storage_path,
    delete_file,
    save_metadata,
)
from server.api import get_handler


def log(message):
    """Print one server handler log line immediately."""
    print(f"[server] {message}", flush=True)


class ServerState:
    """Own the server metadata, versions, tombstones, and storage paths."""

    def __init__(self):
        """Load the server source of truth from disk."""
        self.lock = threading.Lock()
        self.metadata = load_metadata()

    def register_client(self, client_id):
        """Remember a connected client id in server metadata."""
        with self.lock:
            if client_id not in self.metadata["clients"]:
                self.metadata["clients"].append(client_id)
                self.save_locked()

    def list_files(self):
        """Return current active file metadata."""
        with self.lock:
            return self.copy_records_locked(self.metadata["files"])

    def snapshot_for_client(self, client_id):
        """Return active files and unseen deletions for a client."""
        with self.lock:
            return {
                "files": self.copy_records_locked(self.metadata["files"]),
                "deleted": self.unseen_deleted_locked(client_id),
            }

    def save_file(self, request, payload):
        """Store a new or updated file and record its server version."""
        filename = clean_filename(request.get("filename"))
        client_id = request.get("client_id")
        mtime = float(request.get("mtime", 0.0))
        with self.lock:
            path = write_file(filename, payload)
            previous = self.previous_record_locked(filename)
            version = int(previous.get("version", 0)) + 1
            record = build_file_metadata(filename, path, version, client_id, mtime)
            self.metadata["files"][filename] = record
            self.metadata["deleted"].pop(filename, None)
            self.save_locked()
            return dict(record)

    def read_file(self, filename):
        """Read a stored file payload and metadata."""
        safe_name = clean_filename(filename)
        with self.lock:
            metadata = self.metadata["files"].get(safe_name)
            if metadata is None:
                raise FileNotFoundError(safe_name)
            path = storage_path(safe_name)
            with open(path, "rb") as file_obj:
                payload = file_obj.read()
            return {"metadata": dict(metadata), "payload": payload}

    def delete_file(self, request):
        """Remove a stored file and create a delete tombstone."""
        filename = clean_filename(request.get("filename"))
        origin_client = request.get("client_id")
        with self.lock:
            old_record = self.metadata["files"].pop(filename, None)
            if old_record is None:
                raise FileNotFoundError(filename)
            delete_file(filename)
            version = int(old_record.get("version", 0)) + 1
            tombstone = {
                "filename": filename,
                "mtime": float(request.get("mtime", old_record.get("mtime", 0.0))),
                "version": version,
                "origin_client": origin_client,
                "seen_by": [origin_client],
            }
            self.metadata["deleted"][filename] = tombstone
            self.save_locked()
            return dict(tombstone)

    def mark_deletions_seen(self, client_id, filenames):
        """Mark client-visible delete tombstones as applied."""
        safe_names = [clean_filename(filename) for filename in filenames]
        with self.lock:
            for filename in safe_names:
                self.mark_one_deletion_seen_locked(client_id, filename)
            self.remove_seen_deletions_locked()
            self.save_locked()

    def previous_record_locked(self, filename):
        """Return the newest known file or tombstone record."""
        file_record = self.metadata["files"].get(filename)
        return file_record or self.metadata["deleted"].get(filename, {})

    def copy_records_locked(self, records):
        """Return copied metadata records while the state lock is held."""
        return {filename: dict(record) for filename, record in records.items()}

    def unseen_deleted_locked(self, client_id):
        """Return deleted records not yet seen by client_id."""
        return {filename: dict(record) for filename, record in self.metadata["deleted"].items() if client_id not in record["seen_by"]}

    def mark_one_deletion_seen_locked(self, client_id, filename):
        """Add client_id to one tombstone seen list while locked."""
        tombstone = self.metadata["deleted"].get(clean_filename(filename))
        if tombstone is None:
            return
        if client_id not in tombstone["seen_by"]:
            tombstone["seen_by"].append(client_id)

    def remove_seen_deletions_locked(self):
        """Remove tombstones seen by every known client."""
        clients = set(self.metadata["clients"])
        for filename, tombstone in list(self.metadata["deleted"].items()):
            if clients.issubset(set(tombstone.get("seen_by", []))):
                self.metadata["deleted"].pop(filename)

    def save_locked(self):
        """Persist metadata while the state lock is held."""
        save_metadata(self.metadata)


def handle_client(sock, address, state):
    """Serve one connected client until it disconnects."""
    log(f"client connected: {address}")
    with sock:
        while True:
            try:
                message = read_message(sock)
                if message is None:
                    break
                log_request(message, address)
                header, payload = dispatch_message(message, state)
                send_message(sock, header, payload)
                log_response(header, payload, address)
            except ValueError as error:
                log(f"bad request from {address}: {error}")
                send_bad_request(sock, str(error))
            except OSError as error:
                log(f"socket issue for {address}: {error}")
                break
    log(f"client disconnected: {address}")


def log_request(message, address):
    """Log an incoming client request."""
    request, payload = message
    action = request.get("action", "UNKNOWN")
    filename = request.get("filename", "")
    log(f"{address} -> {action} {filename} payload={len(payload)}")


def log_response(header, payload, address):
    """Log one server response sent to a client."""
    action = header.get("action", "UNKNOWN")
    message = header.get("message", "")
    log(f"{address} <- {action} {message} payload={len(payload)}")


def dispatch_message(message, state):
    """Dispatch a decoded message to the matching request handler."""
    request, payload = message
    handler = get_handler(request.get("action"))
    if handler is None:
        return error(ERROR_UNKNOWN_ACTION, "unknown action"), b""
    response = handler(state, request, payload)
    return normalize_response(response)


def normalize_response(response):
    """Return a response as a header and payload pair."""
    if isinstance(response, tuple):
        return response
    return response, b""


def send_bad_request(sock, message):
    """Send a BAD_REQUEST response if the socket is still writable."""
    try:
        send_message(sock, error(ERROR_BAD_REQUEST, message))
    except OSError:
        pass
