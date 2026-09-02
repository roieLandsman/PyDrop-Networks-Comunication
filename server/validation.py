"""Server-side request validation helpers."""

from pathlib import Path

from server.constants import *
from server.file_utils import sha256_bytes
from server.protocol import error
    

def validate_file_message(request: dict, payload: bytes) -> dict | None:
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
        
    try:
        float(request.get("mtime", 0.0))
    except ValueError:
        return error(ERROR_BAD_REQUEST, "mtime must be provided")
    except TypeError:
        return error(ERROR_BAD_REQUEST, "mtime must be a number")
        
    if not isinstance(filename, str) or not filename:
        return error(ERROR_INVALID_FILENAME, "filename is required"")
    if filename in (".", "..") or "/" in filename or "\\" in filename:
        return error(ERROR_INVALID_FILENAME, "filename must be a plain relative name")
    if Path(filename).is_absolute():
        return error(ERROR_INVALID_FILENAME, "filename must not be absolute")
    return None


def validate_client_id(request: dict) -> dict | None:
    """Validate that the request has a client id."""
    if not request.get("client_id"):
        return error(ERROR_BAD_REQUEST, "client_id is required")
    return None


def validate_empty_payload(payload: bytes, request_name: str) -> dict | None:
    """Validate that a request did not send a payload."""
    if payload:
        return error(ERROR_BAD_REQUEST, f"{request_name} must not include a payload")
    return None


def validate_filenames_list(request: dict) -> dict | None:
    """Validate that the request filenames field is a list."""
    if not isinstance(request.get("filenames"), list):
        return error(ERROR_BAD_REQUEST, "filenames must be a list")
    return None
