from hashlib import sha256
from pathlib import Path
from server.constants import STORAGE_DIR, BUFFER_SIZE


def storage_path(filename: str) -> Path:
    "returns the full path of a file"
    return STORAGE_DIR / filename


def sha256_bytes(payload: bytes) -> str:
    "return sha256 hash of a given payload"
    return sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    "return sha256 hash of a given file"
    digest = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(BUFFER_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_file(filename: str, payload: bytes) -> Path:
    "create and save a new. write the content from payload"
    path = storage_path(filename)
    with open(path, "wb") as file_obj:
        file_obj.write(payload)
    return path


def build_file_metadata(filename: str, path: Path, version: int, origin_client: str, mtime: float) -> dict:
    "create a metadata for a single file"
    return {
        "filename": filename,
        "size": path.stat().st_size,
        "mtime": mtime,
        "hash": sha256_file(path),
        "version": version,
        "origin_client": origin_client,
    }
