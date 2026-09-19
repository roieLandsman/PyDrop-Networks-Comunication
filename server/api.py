"""Server-side request handlers for the PyDrop socket API.

Each public function represents one unique request type accepted by the server.
The server API layer is standalone and must not import client code or shared
runtime modules.
"""
from server.constants import *
from log import log
from server.protocol import ack, ack_with_payload, error
from server.validation import (
    validate_client_id,
    validate_empty_payload,
    validate_filename,
    validate_file_message,
    validate_filenames_list,
    validate_version,
)
    
    
def handle_connect(server, request: dict, payload: bytes = b"") -> tuple[dict, bytes]:
    """Handle a CONNECT request."""
    client_id = request.get("client_id")
    val_err = validate_client_id(request)
    if val_err:
        return val_err, b""
    val_err = validate_empty_payload(payload, "CONNECT")
    if val_err:
        return val_err, b""
    server.add_new_client(client_id)
    return ack("Client connected", client_id=client_id)


def handle_list_files(server, request: dict, payload: bytes = b"") -> tuple[dict, bytes]:
    """Handle a LIST_FILES request."""
    val_err = validate_client_id(request)
    if val_err:
        return val_err, b""
    return ack_with_payload("File list returned", {"files": server.list_files()})


def handle_upload(server, request: dict, payload: bytes = b"") -> tuple[dict, bytes]:
    """Handle an UPLOAD request."""
    val_err = validate_file_message(request, payload)
    if val_err:
        return val_err, b""
    try:
        metadata = server.save_file(request, payload)
    except PermissionError as exception:
        log.error(f"upload rejected: {exception}")
        return error(ERROR_STALE_VERSION, str(exception)), b""
    return ack("Upload accepted", metadata=metadata)


def handle_update(server, request: dict, payload: bytes = b"") -> tuple[dict, bytes]:
    """Handle an UPDATE request."""
    val_err = validate_file_message(request, payload)
    if val_err:
        return val_err, b""
    try:
        metadata = server.save_file(request, payload)
    except PermissionError as exception:
        log.error(f"update rejected: {exception}")
        return error(ERROR_STALE_VERSION, str(exception)), b""
    return ack("Update accepted", metadata=metadata)


def handle_download(server, request: dict, payload: bytes = b"") -> tuple[dict, bytes]:
    """Handle a DOWNLOAD request."""
    val_err = validate_client_id(request)
    if val_err:
        return val_err, b""
    val_err = validate_empty_payload(payload, "DOWNLOAD")
    if val_err:
        return val_err, b""
    val_err = validate_filename(request.get("filename"))
    if val_err:
        return val_err, b""
    try:
        result = server.read_file(request.get("filename"))
    except FileNotFoundError:
        log.error(f"download rejected, file not found: {request.get('filename')}")
        return error(ERROR_FILE_NOT_FOUND, "file was not found"), b""
    except ValueError as exception:
        log.error(f"download rejected: {exception}")
        return error(ERROR_INVALID_FILENAME, str(exception)), b""
    header, _ = ack("Download ready", metadata=result["metadata"])
    return header, result["payload"]


def handle_delete(server, request: dict, payload: bytes = b"") -> tuple[dict, bytes]:
    """Handle a DELETE request."""
    val_err = validate_client_id(request)
    if val_err:
        return val_err, b""
    val_err = validate_filename(request.get("filename"))
    if val_err:
        return val_err, b""
    val_err = validate_version(request.get("version"))
    if val_err:
        return val_err, b""
    try:
        result = server.delete_file(request)
    except PermissionError as exception:
        log.error(f"delete rejected: {exception}")
        return error(ERROR_STALE_VERSION, str(exception)), b""
    except FileNotFoundError:
        log.error(f"delete rejected, file not found: {request.get('filename')}")
        return error(ERROR_FILE_NOT_FOUND, "file was not found"), b""
    except ValueError as exception:
        log.error(f"delete rejected: {exception}")
        return error(ERROR_INVALID_FILENAME, str(exception)), b""
    return ack("Delete accepted", metadata=result)


def handle_check_updates(server, request: dict, payload: bytes = b"") -> tuple[dict, bytes]:
    """Handle a CHECK_UPDATES request."""
    val_err = validate_client_id(request)
    if val_err:
        return val_err, b""
    return ack_with_payload("Snapshot returned", server.snapshot_for_client(request.get("client_id")))


def handle_delete_seen(server, request: dict, payload: bytes = b"") -> tuple[dict, bytes]:
    """Handle a DELETE_SEEN request."""
    val_err = validate_client_id(request)
    if val_err:
        return val_err, b""
    val_err = validate_filenames_list(request)
    if val_err:
        return val_err, b""
    
    filenames = request.get("filenames")
    try:
        server.update_deletion_seen_by_client(request.get("client_id"), filenames)
    except ValueError as exception:
        log.error(f"delete seen rejected: {exception}")
        return error(ERROR_INVALID_FILENAME, str(exception)), b""
    return ack("Deletions marked seen", metadata={"filenames": filenames})


def create_message(action: str, request: dict, payload: bytes, server) -> [dict, bytes]:
    """Create a decoded message to the matching action"""
    match action:
        case "CONNECT": return handle_connect(server, request, payload)
        case "LIST_FILES": return handle_list_files(server, request, payload)
        case "UPLOAD": return handle_upload(server, request, payload)
        case "UPDATE": return handle_update(server, request, payload)
        case "DOWNLOAD": return handle_download(server, request, payload)
        case "DELETE": return handle_delete(server, request, payload)
        case "CHECK_UPDATES": return handle_check_updates(server, request, payload)
        case "DELETE_SEEN": return handle_delete_seen(server, request, payload)
        case _: return error(ERROR_UNKNOWN_ACTION, "unknown action"), b""
