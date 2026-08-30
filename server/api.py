"""Server-side request handlers for the PyDrop socket API.

Each public function represents one unique request type accepted by the server.
The server API layer is standalone and must not import client code or shared
runtime modules.
"""
import json

from server.constants import *
from server.file_utils import clean_filename, sha256_bytes
from server.protocol import ack, error


def handle_connect(state, request, payload=b""):
    """Handle a CONNECT request."""
    client_id = request.get("client_id")
    if not client_id:
        return error(ERROR_BAD_REQUEST, "client_id is required")
    state.register_client(client_id)
    return ack("Client connected", client_id=client_id)


def handle_list_files(state, request, payload=b""):
    """Handle a LIST_FILES request."""
    if not request.get("client_id"):
        return error(ERROR_BAD_REQUEST, "client_id is required")
    return json_ack("File list returned", {"files": state.list_files()})


def handle_upload(state, request, payload=b""):
    """Handle an UPLOAD request."""
    validation_error = _validate_file_message(request, payload)
    if validation_error:
        return validation_error
    result = state.save_file(request, payload)
    return ack("Upload accepted", **result)


def handle_update(state, request, payload=b""):
    """Handle an UPDATE request."""
    validation_error = _validate_file_message(request, payload)
    if validation_error:
        return validation_error
    result = state.save_file(request, payload)
    return ack("Update accepted", **result)


def handle_download(state, request, payload=b""):
    """Handle a DOWNLOAD request."""
    if not request.get("client_id"):
        return error(ERROR_BAD_REQUEST, "client_id is required")
    if payload:
        return error(ERROR_BAD_REQUEST, "DOWNLOAD must not include a payload")
    try:
        result = state.read_file(request.get("filename"))
    except FileNotFoundError:
        return error(ERROR_FILE_NOT_FOUND, "file was not found")
    except ValueError as exception:
        return error(ERROR_INVALID_FILENAME, str(exception))
    header = ack("Download ready", **result["metadata"])
    return header, result["payload"]


def handle_delete(state, request, payload=b""):
    """Handle a DELETE request."""
    if not request.get("client_id"):
        return error(ERROR_BAD_REQUEST, "client_id is required")
    try:
        result = state.delete_file(request)
    except FileNotFoundError:
        return error(ERROR_FILE_NOT_FOUND, "file was not found")
    except ValueError as exception:
        return error(ERROR_INVALID_FILENAME, str(exception))
    return ack("Delete accepted", **result)


def handle_check_updates(state, request, payload=b""):
    """Handle a CHECK_UPDATES request."""
    client_id = request.get("client_id")
    if not client_id:
        return error(ERROR_BAD_REQUEST, "client_id is required")
    snapshot = state.snapshot_for_client(client_id)
    return json_ack("Snapshot returned", snapshot)


def handle_delete_seen(state, request, payload=b""):
    """Handle a DELETE_SEEN request."""
    client_id = request.get("client_id")
    filenames = request.get("filenames")
    if not client_id:
        return error(ERROR_BAD_REQUEST, "client_id is required")
    if not isinstance(filenames, list):
        return error(ERROR_BAD_REQUEST, "filenames must be a list")
    try:
        state.mark_deletions_seen(client_id, filenames)
    except ValueError as exception:
        return error(ERROR_INVALID_FILENAME, str(exception))
    return ack("Deletions marked seen", filenames=filenames)


def _validate_file_message(request, payload):
    """Validate a file transfer request."""
    if not request.get("client_id"):
        return error(ERROR_BAD_REQUEST, "client_id is required")
    try:
        expected_size = int(request.get("size", 0))
    except (TypeError, ValueError):
        return error(ERROR_BAD_REQUEST, "size must be an integer")
    if expected_size != len(payload):
        return error(ERROR_PAYLOAD_SIZE_MISMATCH, "payload size mismatch")
    if request.get("hash") != sha256_bytes(payload):
        return error(ERROR_HASH_MISMATCH, "payload hash mismatch")
    mtime_error = _validate_mtime(request)
    if mtime_error:
        return mtime_error
    try:
        clean_filename(request.get("filename"))
    except ValueError as exception:
        return error(ERROR_INVALID_FILENAME, str(exception))
    return None


def _validate_mtime(request):
    """Validate an optional mtime header value."""
    try:
        float(request.get("mtime", 0.0))
    except (TypeError, ValueError):
        return error(ERROR_BAD_REQUEST, "mtime must be a number")
    return None


def json_ack(message, document):
    """Build an ACK response with a JSON payload body."""
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    return ack(message, content_type="application/json"), payload


def get_handler(action: str):
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
