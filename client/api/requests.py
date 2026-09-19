"""Client-side request builders for the PyDrop socket API.

Each public function represents one unique client request type. The client API
layer is standalone and must not import server code or shared runtime modules.
"""

from client.validation import validate_client_id, validate_filename
from client.validation import validate_file_values, validate_filenames_list
from client.validation import validate_version


def connect(client_id: str) -> dict:
    """Build a CONNECT request header."""
    validate_client_id(client_id)
    return {
        "action": "CONNECT",
        "client_id": client_id,
        "size": 0,
    }


def list_files(client_id: str) -> dict:
    """Build a LIST_FILES request header."""
    validate_client_id(client_id)
    return {
        "action": "LIST_FILES",
        "client_id": client_id,
        "size": 0,
    }


def upload(
    client_id: str,
    filename: str,
    size: int,
    mtime: float,
    file_hash: str,
) -> dict:
    """Build an UPLOAD request header for a new file payload."""
    validate_client_id(client_id)
    validate_filename(filename)
    validate_file_values(size, mtime, file_hash)
    return {
        "action": "UPLOAD",
        "client_id": client_id,
        "filename": filename,
        "size": size,
        "mtime": mtime,
        "hash": file_hash,
    }


def update(
    client_id: str,
    filename: str,
    size: int,
    mtime: float,
    file_hash: str,
    version: int | None = None,
) -> dict:
    """Build an UPDATE request header for an existing file payload."""
    validate_client_id(client_id)
    validate_filename(filename)
    validate_file_values(size, mtime, file_hash)
    validate_version(version)
    request = {
        "action": "UPDATE",
        "client_id": client_id,
        "filename": filename,
        "size": size,
        "mtime": mtime,
        "hash": file_hash,
    }
    if version is not None:
        request["version"] = version
    return request


def download(client_id: str, filename: str) -> dict:
    """Build a DOWNLOAD request header."""
    validate_client_id(client_id)
    validate_filename(filename)
    return {
        "action": "DOWNLOAD",
        "client_id": client_id,
        "filename": filename,
        "size": 0,
    }


def delete(client_id: str, filename: str, version: int | None = None) -> dict:
    """Build a DELETE request header."""
    validate_client_id(client_id)
    validate_filename(filename)
    validate_version(version)
    request = {
        "action": "DELETE",
        "client_id": client_id,
        "filename": filename,
        "size": 0,
    }
    if version is not None:
        request["version"] = version
    return request


def delete_seen(client_id: str, filenames: list[str]) -> dict:
    """Build a DELETE_SEEN request header."""
    validate_client_id(client_id)
    validate_filenames_list(filenames)
    return {
        "action": "DELETE_SEEN",
        "client_id": client_id,
        "filenames": filenames,
        "size": 0,
    }


def check_updates(client_id: str) -> dict:
    """Build a CHECK_UPDATES request header."""
    validate_client_id(client_id)
    return {
        "action": "CHECK_UPDATES",
        "client_id": client_id,
        "size": 0,
    }
