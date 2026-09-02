"""Server-side PyDrop file hashing, metadata, and path helpers."""

from hashlib import sha256
import json
from pathlib import Path
from server.constants import STORAGE_DIR, METADATA_FILE, BUFFER_SIZE


def storage_path(filename: str) -> Path:
    """Return the safe storage path for a file name."""
    return STORAGE_DIR / filename


def sha256_bytes(payload: bytes) -> str:
    """Return the SHA-256 hex digest for bytes."""
    return sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest for a file."""
    digest = sha256()
    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(BUFFER_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_file(filename: str, payload: bytes) -> Path:
    """Store payload bytes under the safe server storage path."""
    path = storage_path(filename)
    with open(path, "wb") as file_obj:
        file_obj.write(payload)
    return path


def delete_file(filename: str) -> None:
    """Delete a stored file if it exists."""
    path = storage_path(filename)
    if path.exists():
        path.unlink()


def build_file_metadata(filename: str, path: Path, version: int, origin_client: str, mtime: float) -> dict:
    """Build a metadata dictionary for one stored file.""")
    return {
        "filename": filename,
        "size": path.stat().st_size,
        "mtime": mtime,
        "hash": sha256_file(path),
        "version": version,
        "origin_client": origin_client,
    }
