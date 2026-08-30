"""Server-side PyDrop file hashing, metadata, and path helpers."""

from hashlib import sha256
import json
from pathlib import Path

from server.constants import STORAGE_DIR, METADATA_FILE, BUFFER_SIZE


def default_metadata() -> dict:
    """Return an empty server metadata document."""
    return {"files": {}, "deleted": {}, "clients": []}


def clean_filename(filename: str) -> str:
    """Return a safe plain file name or raise ValueError."""
    if not isinstance(filename, str) or not filename:
        raise ValueError("filename is required")
    if filename in (".", "..") or "/" in filename or "\\" in filename:
        raise ValueError("filename must be a plain relative name")
    if Path(filename).is_absolute():
        raise ValueError("filename must not be absolute")
    return filename


def storage_path(filename) -> Path:
    """Return the safe storage path for a file name."""
    return STORAGE_DIR / clean_filename(filename)


def sha256_bytes(payload):
    """Return the SHA-256 hex digest for bytes."""
    return sha256(payload).hexdigest()


def sha256_file(path):
    """Return the SHA-256 hex digest for a file."""
    digest = sha256()
    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(BUFFER_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_metadata():
    """Load server metadata from disk."""
    if not METADATA_FILE.exists():
        return default_metadata()
    with open(METADATA_FILE, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def save_metadata(metadata):
    """Write server metadata to disk."""
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as file_obj:
        json.dump(metadata, file_obj, indent=2, sort_keys=True)


def write_file(filename, payload):
    """Store payload bytes under the safe server storage path."""
    path = storage_path(filename)
    with open(path, "wb") as file_obj:
        file_obj.write(payload)
    return path


def delete_file(filename):
    """Delete a stored file if it exists."""
    path = storage_path(filename)
    if path.exists():
        path.unlink()


def build_file_metadata(filename, path, version, origin_client, mtime) -> dict:
    """Build a metadata dictionary for one stored file."""
    stat_result = path.stat()
    return {
        "filename": filename,
        "size": stat_result.st_size,
        "mtime": mtime,
        "hash": sha256_file(path),
        "version": version,
        "origin_client": origin_client,
    }
