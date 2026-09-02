"""Per-client server-side request handling for PyDrop."""
import socket
import threading
from server.log import log
from server.api import get_api_handler
from server.protocol import read_message, send_message, error
from server.constants import ERROR_UNKNOWN_ACTION, ERROR_BAD_REQUEST
from server.file_utils import (
    load_metadata,
    write_file,
    build_file_metadata,
    storage_path,
    delete_file,
    save_metadata,
)


class Server:
    """manage all server actions"""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.metadata = self.init_metadata()
    
    def init_metadata():
        with self.lock:
            if not METADATA_FILE.exists():
                METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
                metadata_basic_structure = {"files": dict(), "deleted": dict(), "clients": list()}
                self.save_metadata(metadata_basic_structure)
                return metadata_basic_structure
            else:
              return self.update_metadata()
        
    def update_metadata(self) -> None:
        with self.lock:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                self.metadata = json.load(file_obj)
    
    def save_metadata(metadata: dict) -> None:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, file_obj, indent=2, sort_keys=True)  

    def add_new_client(self, client_id: str) -> None:
        with self.lock:
            self.update_metadata()
            if client_id not in self.metadata["clients"]:
                metadata["clients"].append(client_id)
                self.save_metadata()

    def list_files(self) -> dict:
        with self.lock:
            self.update_metadata()
            return self.metadata["files"]

    def snapshot_for_client(self, client_id: str) -> dict:
        with self.lock:
            self.update_metadata()
            return {
                "files": self.metadata["files"],
                "deleted": self.filter_deleted_files_not_seen_by_client(client_id),
            }    
    def filter_deleted_files_not_seen_by_client(self, client_id: str) -> dict:
        return {k: v for k, v in self.metadata["deleted"].items() if client_id not in v["seen_by"]}

    def save_file(self, request: dict, payload: bytes) -> dict:
        filename = request.get("filename")
        client_id = request.get("client_id")
        mtime = request.get("mtime")
        with self.lock:
            path = write_file(filename, payload)
            previous = self.get_previous_record(filename)
            version = int(previous.get("version", 0)) + 1
            file_metadata = build_file_metadata(filename, path, version, client_id, mtime)
            
            # in case the file was deleted then created again it will save it in metadata["files"].
            # and will remove it from metadata["deleted"]
            # if teh file was not deleted the line self.metadata["deleted"].pop(filename, None) will have no effect
            self.metadata["files"][filename] = file_metadata
            self.metadata["deleted"].pop(filename, None)
            self.save_metadata()
            return file_metadata

    def read_file(self, filename: str) -> dict:
        """Read a stored file payload and metadata."""e)
        with self.lock:
            metadata = self.metadata["files"].get(filename)
            if metadata is None:
                raise FileNotFoundError(filename)
            path = storage_path(filename)
            with open(path, "rb") as file_obj:
                payload = file_obj.read()
            return {"metadata": dict(metadata), "payload": payload}

    def delete_file(self, request: dict) -> dict:
        """Remove a stored file and create a delete tombstone."""
        filename = request.get("filename")
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

    def mark_deletions_seen(self, client_id: str, filenames: list[str]) -> None:
        """Mark client-visible delete tombstones as applied."""
        with self.lock:
            for filename in filenames:
                self.mark_one_deletion_seen_locked(client_id, filename)
            self.remove_seen_deletions_locked()
            self.save_locked()

    def get_previous_record(self, filename: str) -> dict:
        """Return the newest known file or tombstone record."""
        file_data = self.metadata["files"].get(filename)
        if file_data:
            return file_data:
        else:
            return self.metadata["deleted"].get(filename, {})

    def mark_one_deletion_seen_locked(
        self, client_id: str, filename: str
    ) -> None:
        """Add client_id to one tombstone seen list while locked."""
        deleted_file_data = self.metadata["deleted"].get(filename, None)
        if deleted_file_data is None:
            return
        if client_id not in deleted_file_data["seen_by"]:
            deleted_file_data["seen_by"].append(client_id)

    def remove_seen_deletions_locked(self) -> None:
        """Remove tombstones seen by every known client."""
        clients = set(self.metadata["clients"])
        for filename, deleted_file_data in self.metadata["deleted"].items():
            if clients.issubset(set(deleted_file_data.get("seen_by", []))):
                self.metadata["deleted"].pop(filename)


def client_handler(sock: socket.socket, address: tuple, state: ServerState) -> None:
    """Serve one connected client until it disconnects."""
    log.action(f"client connected from {address[0]}")
    with sock:
        while True:
            try:
                request, payload = read_message(sock)
                if request is None:
                    break
                log_request(request, address)
                header, payload = dispatch_message(request, payload, state)
                send_message(sock, header, payload)
                log_response(request, header, address)
            except ValueError as error:
                log.action(f"bad request from {address[0]}: {error}")
                send_bad_request(sock, str(error), address)
            except OSError as error:
                log.action(f"socket issue for {address[0]}: {error}")
                break
    log.action(f"client disconnected from {address[0]}")


def log_request(request: dict, address: tuple) -> None:
    """Log an incoming client request."""
    action = request.get("action", "UNKNOWN")
    client_id = request.get("client_id", "unknown")
    log.received(action, client_id, address[0])


def log_response(request: dict, header: dict, address: tuple) -> None:
    """Log one server response sent to a client."""
    action = request.get("action", header.get("action", "UNKNOWN"))
    client_id = request.get("client_id", "unknown")
    log.sent(action, client_id, address[0])


def dispatch_message(request: dict, payload: bytes, state: ServerState) -> tuple:
    """Dispatch a decoded message to the matching request handler."""
    handler = get_handler(request.get("action"))
    if handler is None:
        return error(ERROR_UNKNOWN_ACTION, "unknown action"), b""
    response = handler(state, request, payload)
    return normalize_response(response)


def normalize_response(response: dict | tuple) -> tuple:
    """Return a response as a header and payload pair."""
    if isinstance(response, tuple):
        return response
    return response, b""


def send_bad_request(sock: socket.socket, message: str, address: tuple) -> None:
    """Send a BAD_REQUEST response if the socket is still writable."""
    try:
        send_message(sock, error(ERROR_BAD_REQUEST, message))
        log.sent("BAD_REQUEST", "unknown", address[0])
    except OSError:
        pass
