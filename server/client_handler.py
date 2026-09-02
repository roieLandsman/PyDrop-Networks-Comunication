
import json
import threading
from socket import socket
from server.log import log
from server.api import get_api_handler
from server.protocol import read_message, send_message, error
from server.constants import METADATA_FILE, ERROR_UNKNOWN_ACTION, ERROR_BAD_REQUEST
from server.file_utils import write_file, build_file_metadata, storage_path


class Server:
    """manage all server actions"""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.metadata: dict = {"files": dict(), "deleted": dict(), "clients": list()}
        self.init_metadata()
    
    def init_metadata(self) -> None:
        with self.lock:
            if not METADATA_FILE.exists():
                METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
                self.save_metadata()
            else:
                self.update_metadata()
        
    def update_metadata(self) -> None:
        with self.lock:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
    
    def save_metadata(self) -> None:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, sort_keys=True)  

    def add_new_client(self, client_id: str) -> None:
        with self.lock:
            self.update_metadata()
            if client_id not in self.metadata["clients"]:
                self.metadata["clients"].append(client_id)
                self.save_metadata()

    def list_files(self) -> dict:
        with self.lock:
            self.update_metadata()
            return self.metadata["files"].copy()

    def snapshot_for_client(self, client_id: str) -> dict:
        with self.lock:
            self.update_metadata()
            return {
                "files": self.metadata["files"].copy(),
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
            # if the file was not deleted the line self.metadata["deleted"].pop(filename, None) will have no effect
            self.metadata["files"][filename] = file_metadata
            self.metadata["deleted"].pop(filename, None)
            self.save_metadata()
            return file_metadata

    def read_file(self, filename: str) -> dict:
        """Read a stored file payload and metadata."""
        with self.lock:
            metadata = self.metadata["files"].get(filename, None)
            if metadata is None:
                raise FileNotFoundError(filename)
            path = storage_path(filename)
            with open(path, "rb") as f:
                payload = f.read()
            return {"metadata": metadata, "payload": payload}

    def delete_file(self, request: dict) -> dict:
        """Remove a stored file and create a delete tombstone."""
        filename = request.get("filename")
        client_id = request.get("client_id")
        with self.lock:
            old_record = self.metadata["files"].pop(filename, None)
            if old_record is None:
                raise FileNotFoundError(filename)
            
            # delete the file
            path = storage_path(filename)
            if path.exists():
                path.unlink()
            
            version = int(old_record.get("version", 0)) + 1
            self.metadata["deleted"][filename] = {
                "mtime": float(request.get("mtime", old_record.get("mtime", 0.0))),
                "version": version,
                "origin_client": client_id,
                "seen_by": [client_id],
            }
            self.save_metadata()
            return self.metadata["deleted"][filename]

    def update_deletion_seen_by_client(self, client_id: str, filenames: list[str]) -> None:
        """Mark client-visible delete tombstones as applied."""
        with self.lock:
            for filename in filenames:
                deleted_file_data = self.metadata["deleted"].get(filename, None)
                if deleted_file_data is None:
                    continue
                if client_id not in deleted_file_data["seen_by"]:
                    deleted_file_data["seen_by"].append(client_id)
            
            clients = set(self.metadata["clients"])
            filenames_to_pop = set()
            for filename, deleted_file_data in self.metadata["deleted"].items():
                # using issubset make sure all existing clients saw the delition
                # while making sure that if a client disconnected from the server 
                # before seeing the deletion it will not break
                if clients.issubset(set(deleted_file_data.get("seen_by", []))):
                    filenames_to_pop.add(filename)
            for filename in filenames_to_pop:
                self.metadata["deleted"].pop(filename)
            
            self.save_metadata()

        

    def get_previous_record(self, filename: str) -> dict:
        """Return the newest known file or tombstone record."""
        file_data = self.metadata["files"].get(filename)
        if file_data:
            return file_data
        else:
            return self.metadata["deleted"].get(filename, {})


    def remove_seen_deletions_locked(self) -> None:
        """Remove tombstones seen by every known client."""
        clients = set(self.metadata["clients"])
        for filename, deleted_file_data in self.metadata["deleted"].items():
            if clients.issubset(set(deleted_file_data.get("seen_by", []))):
                self.metadata["deleted"].pop(filename)


def client_handler(sock: socket, address: tuple, server: Server) -> None:
    """Serve one connected client until it disconnects."""
    log.action(f"client connected from {address[0]}")
    with sock:
        while True:
            try:
                request, payload = read_message(sock)
                if request is None:
                    break
                log.received(request.get("action", "UNKNOWN"), request.get("client_id", "unknown"), address[0])
                header, payload = dispatch_message(request, payload, server)
                send_message(sock, header, payload)
                log.sent(request.get("action", "UNKNOWN"), request.get("client_id", "unknown"), address[0])
            except ValueError as error:
                log.action(f"bad request from {address[0]}: {error}")
                send_bad_request(sock, str(error), address)
            except OSError as error:
                log.action(f"socket issue for {address[0]}: {error}")
                break
    log.action(f"client disconnected from {address[0]}")


def dispatch_message(request: dict, payload: bytes, server: Server) -> tuple:
    """Dispatch a decoded message to the matching request handler."""
    handler = get_api_handler(request.get("action"))
    if handler is None:
        return error(ERROR_UNKNOWN_ACTION, "unknown action"), b""
    else:
        response = handler(server, request, payload)
        return normalize_response(response)


def normalize_response(response: dict | tuple) -> tuple:
    """Return a response as a header and payload pair."""
    if isinstance(response, tuple):
        return response
    else:
        return response, b""


def send_bad_request(sock: socket, message: str, address: tuple) -> None:
    """Send a BAD_REQUEST response if the socket is still writable."""
    try:
        send_message(sock, error(ERROR_BAD_REQUEST, message))
        log.sent("BAD_REQUEST", "unknown", address[0])
    except OSError:
        pass
