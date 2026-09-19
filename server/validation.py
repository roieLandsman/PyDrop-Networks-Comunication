"""Server-side request validation helpers."""

from pathlib import Path

from server.constants import *
from server.file_utils import sha256_bytes
from log import log
from server.protocol import error


def validate_filename(filename) -> dict | None:
    if not filename:
        log.error("validation failed: filename is required")
        return error(ERROR_INVALID_FILENAME, "filename is required")
    if not isinstance(filename, str):
        log.error("validation failed: filename must be a string")
        return error(ERROR_INVALID_FILENAME, "filename must be a string")
    if filename in (".", "..") or "/" in filename or "\\" in filename:
        log.error(f"validation failed: unsafe filename {filename}")
        return error(ERROR_INVALID_FILENAME, "filename must be a plain relative name")
    if Path(filename).is_absolute():
        log.error(f"validation failed: absolute filename {filename}")
        return error(ERROR_INVALID_FILENAME, "filename must not be absolute")
    return None

def validate_file_message(request: dict, payload: bytes) -> dict | None:
    if not request.get("client_id"):
        log.error("validation failed: client_id is required")
        return error(ERROR_BAD_REQUEST, "client_id is required")
        
    try:
        expected_size = int(request.get("size", 0))
    except (TypeError, ValueError):
        log.error("validation failed: size must be an integer")
        return error(ERROR_BAD_REQUEST, "size must be an integer")
        
    if expected_size != len(payload):
        log.error("validation failed: payload size mismatch")
        return error(ERROR_PAYLOAD_SIZE_MISMATCH, "payload size mismatch")
    if request.get("hash") != sha256_bytes(payload):
        log.error("validation failed: payload hash mismatch")
        return error(ERROR_HASH_MISMATCH, "payload hash mismatch")
        
    try:
        float(request.get("mtime", 0.0))
    except ValueError:
        log.error("validation failed: mtime must be provided")
        return error(ERROR_BAD_REQUEST, "mtime must be provided")
    except TypeError:
        log.error("validation failed: mtime must be a number")
        return error(ERROR_BAD_REQUEST, "mtime must be a number")
    
    return validate_filename(request.get('filename', None))
    
    
def validate_empty_payload(payload: bytes, request_name: str) -> dict | None:
    if payload:
        log.error(f"validation failed: {request_name} must not include a payload")
        return error(ERROR_BAD_REQUEST, f"{request_name} must not include a payload")
    return None
    

def validate_client_id(request: dict) -> dict | None:
    if not request.get("client_id"):
        log.error("validation failed: client_id is required")
        return error(ERROR_BAD_REQUEST, "client_id is required")
    return None


def validate_version(version: int | None) -> dict | None:
    """Return an error when version is malformed."""
    if version is None:
        return None
    if not isinstance(version, int) or version < 0:
        log.error("validation failed: version must be a non-negative integer")
        return error(ERROR_BAD_REQUEST, "version must be a non-negative integer")
    return None


def validate_filenames_list(request: dict) -> dict | None:
    filenames = request.get("filenames")
    if not isinstance(filenames, list):
        log.error("validation failed: filenames must be a list")
        return error(ERROR_BAD_REQUEST, "filenames must be a list")
    for filename in filenames:
        status = validate_filename(filename)
        if status:
            return status
    return None
