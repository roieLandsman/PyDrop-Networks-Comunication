from hashlib import sha256
import os
from pathlib import Path
from client.constants import BUFFER_SIZE, SYNC_FOLDER
from client.validation import validate_filename


def sync_path(filename: str, folder: str | Path = SYNC_FOLDER) -> Path:
    "return a valid path of a file in the folder"
    validate_filename(filename)
    return Path(folder) / filename


def sha256_bytes(payload: bytes) -> str:
    "calculate SHA256 hash of a bytes object"
    return sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    "calculate the SHA256 hash of a file"
    digest = sha256()
    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(BUFFER_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_file(filename: str, folder: str | Path = SYNC_FOLDER) -> bytes:
    "read a file and return thr content as bytes"
    with open(sync_path(filename, folder), "rb") as file_obj:
        return file_obj.read()


def write_file(filename: str, payload: bytes, folder: str | Path = SYNC_FOLDER, mtime: float | None = None) -> Path:
    "create or overwrite a file"
    path = sync_path(filename, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as file_obj:
        file_obj.write(payload)
    if mtime is not None:
        # Keep downloaded files close to server metadata for stable scans.
        os.utime(path, (float(mtime), float(mtime)))
    return path


def delete_file(filename: str, folder: str | Path = SYNC_FOLDER) -> None:
    "delete a file"
    path = sync_path(filename, folder)
    if path.exists():
        path.unlink()


def rename_to_local(filename: str, folder: str | Path = SYNC_FOLDER) -> Path:
    "copy a file. name the copy exactly as the origin file but with a .local suffix"
    path = sync_path(filename, folder)
    local_path = sync_path(f"{filename}.local", folder)
    local_path.unlink(missing_ok=True)
    return path.replace(local_path)


def file_metadata(path: Path) -> dict:
    "create metadata of a file"
    validate_filename(path.name)
    stat_result = path.stat()
    return {
        "filename": path.name,
        "size": stat_result.st_size,
        "mtime": stat_result.st_mtime,
        "hash": sha256_file(path),
    }
