"""Server-side request handlers for the PyDrop socket API.

Each public function represents one unique request type accepted by the server.
The server API layer is standalone and must not import client code or shared
runtime modules.
"""
import json
from server.constants import *
from server.protocol import ack, error
from server.validation import (
    validate_client_id,
    validate_empty_payload,
    validate_file_message,
    validate_filenames_list,
)


def handle_connect(server, request: dict, payload: bytes = b"") -> dict:
    """Handle a CONNECT request."""
    client_id = request.get("client_id")
    validation_error = validate_client_id(request)
    if validation_error:
        return validation_error
    server.add_new_client(client_id)
    return ack("Client connected", client_id=client_id)


def handle_list_files(server, request: dict, payload: bytes = b"") -> dict | tuple:
    """Handle a LIST_FILES request."""
    validation_error = validate_client_id(request)
    if validation_error:
        return validation_error
    return ack_with_payload("File list returned", {"files": server.list_files()})


def handle_upload(server, request: dict, payload: bytes = b"") -> dict:
    """Handle an UPLOAD request."""
    validation_error = validate_file_message(request, payload)
    if validation_error:
        return validation_error
    return ack("Upload accepted", metadata=server.save_file(request, payload))


def handle_update(server, request: dict, payload: bytes = b"") -> dict:
    """Handle an UPDATE request."""
    validation_error = validate_file_message(request, payload)
    if validation_error:
        return validation_error
    return ack("Update accepted", metadata=server.save_file(request, payload))


def handle_download(server, request: dict, payload: bytes = b"") -> dict | tuple:
    """Handle a DOWNLOAD request."""
    validation_error = validate_client_id(request)
    if validation_error:
        return validation_error
    validation_error = validate_empty_payload(payload, "DOWNLOAD")
    if validation_error:
        return validation_error
    try:
        result = server.read_file(request.get("filename"))
    except FileNotFoundError:
        return error(ERROR_FILE_NOT_FOUND, "file was not found")
    except ValueError as exception:
        return error(ERROR_INVALID_FILENAME, str(exception))
    header = ack("Download ready", metadata=result["metadata"])
    return header, result["payload"]


def handle_delete(server, request: dict, payload: bytes = b"") -> dict:
    """Handle a DELETE request."""
    validation_error = validate_client_id(request)
    if validation_error:
        return validation_error
    try:
        result = server.delete_file(request)
    except FileNotFoundError:
        return error(ERROR_FILE_NOT_FOUND, "file was not found")
    except ValueError as exception:
        return error(ERROR_INVALID_FILENAME, str(exception))
    return ack("Delete accepted", metadata=result)


def handle_check_updates(server, request: dict, payload: bytes = b"") -> dict | tuple:
    """Handle a CHECK_UPDATES request."""
    client_id = request.get("client_id")
    validation_error = validate_client_id(request)
    if validation_error:
        return validation_error
    snapshot = server.snapshot_for_client(client_id)
    return ack_with_payload("Snapshot returned", snapshot)


def handle_delete_seen(server, request: dict, payload: bytes = b"") -> dict:
    """Handle a DELETE_SEEN request."""
    client_id = request.get("client_id")
    filenames = request.get("filenames")
    validation_error = validate_client_id(request)
    if validation_error:
        return validation_error
    validation_error = validate_filenames_list(request)
    if validation_error:
        return validation_error
    try:
        server.update_deletion_seen_by_client(client_id, filenames)
    except ValueError as exception:
        return error(ERROR_INVALID_FILENAME, str(exception))
    return ack("Deletions marked seen", metadata={"filenames": filenames})


def ack_with_payload(message: str, document: dict) -> tuple:
    """Build an ACK response with a JSON payload body."""
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    return ack(message, content_type="application/json"), payload


def get_api_handler(action: str):
    """Return the handler function for an API action."""
    match action:
        case "CONNECT": return handle_connect
        case "LIST_FILES": return handle_list_files
        case "UPLOAD": return handle_upload
        case "UPDATE": return handle_update
        case "DOWNLOAD": return handle_download
        case "DELETE": return handle_delete
        case "CHECK_UPDATES": return handle_check_updates
        case "DELETE_SEEN": return handle_delete_seen
        case _: return None
