"""Client-side PyDrop file hashing, metadata, and path helpers."""

from hashlib import sha256
import os
from pathlib import Path

from client.constants import BUFFER_SIZE, SYNC_FOLDER


def clean_filename(filename):
    """Return a safe plain file name or raise ValueError."""
    if not isinstance(filename, str) or not filename:
        raise ValueError("filename is required")
    if filename in (".", "..") or "/" in filename or "\\" in filename:
        raise ValueError("filename must be a plain relative name")
    if Path(filename).is_absolute():
        raise ValueError("filename must not be absolute")
    return filename


def sync_path(filename, folder=SYNC_FOLDER):
    """Return the safe local sync path for a file name."""
    return Path(folder) / clean_filename(filename)


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


def read_file(filename, folder=SYNC_FOLDER):
    """Read bytes for a file inside the sync folder."""
    with open(sync_path(filename, folder), "rb") as file_obj:
        return file_obj.read()


def write_file(filename, payload, folder=SYNC_FOLDER, mtime=None):
    """Write bytes to a file inside the sync folder."""
    path = sync_path(filename, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as file_obj:
        file_obj.write(payload)
    if mtime is not None:
        # Keep downloaded files close to server metadata for stable scans.
        os.utime(path, (float(mtime), float(mtime)))
    return path


def delete_file(filename, folder=SYNC_FOLDER):
    """Delete a file inside the sync folder if it exists."""
    path = sync_path(filename, folder)
    if path.exists():
        path.unlink()


def file_metadata(path):
    """Build client-side metadata for one local file."""
    stat_result = path.stat()
    return {
        "filename": clean_filename(path.name),
        "size": stat_result.st_size,
        "mtime": stat_result.st_mtime,
        "hash": sha256_file(path),
    }
