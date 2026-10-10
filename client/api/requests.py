from client.validation import validate_client_id, validate_filename
from client.validation import validate_file_values, validate_filenames_list
from client.validation import validate_version


def connect(client_id: str) -> dict:
    "creates a CONNECT api request"
    validate_client_id(client_id)
    return {
        "action": "CONNECT",
        "client_id": client_id,
        "size": 0,
    }


def upload(client_id: str, filename: str, size: int, mtime: float, file_hash: str) -> dict:
    "creates a UPLOAD api request"
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


def update(client_id: str, filename: str, size: int, mtime: float, file_hash: str, version: int | None = None) -> dict:
    "creates a UPDATE api request"
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
    "creates a DOWNLOAD api request"
    validate_client_id(client_id)
    validate_filename(filename)
    return {
        "action": "DOWNLOAD",
        "client_id": client_id,
        "filename": filename,
        "size": 0,
    }


def delete(client_id: str, filename: str, version: int | None = None) -> dict:
    "creates a DELETE api request"
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
    "creates a DELETE_SEEN api request"
    validate_client_id(client_id)
    validate_filenames_list(filenames)
    return {
        "action": "DELETE_SEEN",
        "client_id": client_id,
        "filenames": filenames,
        "size": 0,
    }


def check_updates(client_id: str) -> dict:
    "creates a CHECK_UPDATES api request"
    validate_client_id(client_id)
    return {
        "action": "CHECK_UPDATES",
        "client_id": client_id,
        "size": 0,
    }
