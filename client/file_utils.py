"""Client-side PyDrop file hashing, metadata, and path helpers."""

from hashlib import sha256
import os
from pathlib import Path

from client.constants import BUFFER_SIZE, SYNC_FOLDER
from client.validation import validate_filename


def sync_path(filename: str, folder: str | Path = SYNC_FOLDER) -> Path:
    """Return the safe local sync path for a file name."""
    validate_filename(filename)
    return Path(folder) / filename


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


def read_file(filename: str, folder: str | Path = SYNC_FOLDER) -> bytes:
    """Read bytes for a file inside the sync folder."""
    with open(sync_path(filename, folder), "rb") as file_obj:
        return file_obj.read()


def write_file(
    filename: str,
    payload: bytes,
    folder: str | Path = SYNC_FOLDER,
    mtime: float | None = None,
) -> Path:
    """Write bytes to a file inside the sync folder."""
    path = sync_path(filename, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as file_obj:
        file_obj.write(payload)
    if mtime is not None:
        # Keep downloaded files close to server metadata for stable scans.
        os.utime(path, (float(mtime), float(mtime)))
    return path


def delete_file(filename: str, folder: str | Path = SYNC_FOLDER) -> None:
    """Delete a file inside the sync folder if it exists."""
    path = sync_path(filename, folder)
    if path.exists():
        path.unlink()


def rename_to_local(filename: str, folder: str | Path = SYNC_FOLDER) -> Path:
    """Rename a synced file to its .local backup name."""
    path = sync_path(filename, folder)
    local_path = sync_path(f"{filename}.local", folder)
    local_path.unlink(missing_ok=True)
    return path.replace(local_path)


def file_metadata(path: Path) -> dict:
    """Build client-side metadata for one local file."""
    validate_filename(path.name)
    stat_result = path.stat()
    return {
        "filename": path.name,
        "size": stat_result.st_size,
        "mtime": stat_result.st_mtime,
        "hash": sha256_file(path),
    }
