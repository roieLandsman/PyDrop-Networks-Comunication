
import json
import threading
from socket import socket
from log import log
from server.api import create_message
from server.protocol import read_message, send_message, error
from server.constants import METADATA_FILE, ERROR_BAD_REQUEST
from server.file_utils import write_file, build_file_metadata, storage_path


class Server:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.metadata: dict = {"files": dict(), "deleted": dict(), "clients": list()}
        self.init_metadata()
    
    def init_metadata(self) -> None:
        "initialize self.metadata or METADATA_FILE only one is needed to align them"
        with self.lock:
            if not METADATA_FILE.exists():
                # will write the default metadata to the file so they will be aligned
                METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
                self.save_metadata()
            else:
                # update self.metadata from the file so they will be aligned
                self.update_metadata()
        
    def update_metadata(self) -> None:
        "load the latest metadata from METADATA_FILE"
        with self.lock:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

    def save_metadata(self) -> None:
        "saves the latest metadata to METADATA_FILE"
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, sort_keys=True)

    def add_new_client(self, client_id: str) -> None:
        "add a new client id to the metadata file"
        with self.lock:
            self.update_metadata()
            if client_id not in self.metadata["clients"]:
                self.metadata["clients"].append(client_id)
                self.save_metadata()

    def filter_deleted_files_not_seen_by_client(self, client_id: str) -> dict:
        "returns all the deleted files that the given client has not yet seen"
        return {k: v for k, v in self.metadata["deleted"].items() if client_id not in v["seen_by"]}

    def snapshot_for_client(self, client_id: str) -> dict:
        "return existing files + deleted files the given client has not yet seen"
        with self.lock:
            self.update_metadata()
            return {
                "files": self.metadata["files"].copy(),
                "deleted": self.filter_deleted_files_not_seen_by_client(client_id),
            }

    def get_previous_record(self, filename: str) -> dict:
        "get the last known record for a file"
        file_data = self.metadata["files"].get(filename)
        if file_data:
            return file_data
        else:
            return self.metadata["deleted"].get(filename, {})

    def validate_write_version(self, request: dict, previous: dict, file_exists: bool) -> None:
        "validate if an upload or update is allowed then accept or reject"
        if request.get("action") == "UPLOAD":
            if file_exists:
                log.error(f"stale upload rejected: {request.get('filename')}")
                raise PermissionError("server already has a newer copy")
            return
        if not previous:
            return
        client_version = int(request.get("version", 0))
        if client_version < int(previous.get("version", 0)):
            log.error(f"stale update rejected: {request.get('filename')}")
            raise PermissionError("server already has a newer copy")

    def save_file(self, request: dict, payload: bytes) -> dict:
        "save new uplaoded file and update the metadata and deletion if needed"
        filename = request.get("filename")
        client_id = request.get("client_id")
        mtime = request.get("mtime")
        with self.lock:
            file_exists = filename in self.metadata["files"]
            previous = self.get_previous_record(filename)
            self.validate_write_version(request, previous, file_exists)
            path = write_file(filename, payload)
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
        "read a file and return his content as binary and metadata"
        with self.lock:
            metadata = self.metadata["files"].get(filename, None)
            if metadata is None:
                log.error(f"download failed, file not found: {filename}")
                raise FileNotFoundError(filename)
            path = storage_path(filename)
            with open(path, "rb") as f:
                payload = f.read()
            return {"metadata": metadata, "payload": payload}

    def delete_file(self, request: dict) -> dict:
        "delete a file, delete his metadata and add to the deleted files list"
        filename = request.get("filename")
        client_id = request.get("client_id")
        with self.lock:
            old_record = self.metadata["files"].get(filename)
            if old_record is None:
                log.error(f"delete failed, file not found: {filename}")
                raise FileNotFoundError(filename)
            client_version = int(request.get("version") or 0)
            server_version = int(old_record.get("version", 0))
            if client_version < server_version:
                log.error(f"stale delete rejected: {filename}")
                raise PermissionError("server already has a newer copy")
            self.metadata["files"].pop(filename)
            
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
        "if all clients saw a deletion - remove the file from the deleted list"
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

def send_bad_request(sock: socket, message: str, address: tuple) -> None:
    "send ERROR_BAD_REQUEST to client"
    try:
        send_message(sock, error(ERROR_BAD_REQUEST, message))
        log.sent("BAD_REQUEST", "unknown", address[0])
    except OSError as error:
        log.error(f"could not send BAD_REQUEST to {address[0]}: {error}")
        pass


def client_handler(sock: socket, address: tuple, server: Server) -> None:
    "handle a connection to a single client"
    log.info(f"client connected from {address[0]}")
    with sock:
        while True:
            try:
                request, payload = read_message(sock)
                if request is None:
                    break
                action = request.get("action", "UNKNOWN")
                client_id = request.get("client_id", "unknown")

                log.received(action, client_id, address[0])
                header, payload = create_message(action, request, payload, server)
                send_message(sock, header, payload)
                log.sent(action, client_id, address[0])

            except ValueError as error:
                log.error(f"bad request from {address[0]}: {error}")
                send_bad_request(sock, str(error), address)
            except OSError as error:
                log.error(f"socket issue for {address[0]}: {error}")
                break
    log.info(f"client disconnected from {address[0]}")
