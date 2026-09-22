from pathlib import Path
from log import log

def validate_client_id(client_id: str) -> None:
    if not isinstance(client_id, str):
        log.error("validation failed: client_id must be a string")
        raise ValueError("client_id must be a string")
    if not client_id.strip():
        log.error("validation failed: client_id is required")
        raise ValueError("client_id is required")


def validate_filename(filename: str) -> None:
    if not isinstance(filename, str):
        log.error("validation failed: filename must be a string")
        raise ValueError("filename must be a string")
    if not filename:
        log.error("validation failed: filename is required")
        raise ValueError("filename is required")
    if filename in (".", "..") or "/" in filename or "\\" in filename:
        log.error(f"validation failed: unsafe filename {filename}")
        raise ValueError("filename must be a plain relative name")
    if Path(filename).is_absolute():
        log.error(f"validation failed: absolute filename {filename}")
        raise ValueError("filename must not be absolute")


def validate_file_values(size: int, mtime: float, file_hash: str) -> None:
    if not isinstance(size, int) or size < 0:
        log.error("validation failed: size must be a non-negative integer")
        raise ValueError("size must be a non-negative integer")
    if not isinstance(mtime, (int, float)):
        log.error("validation failed: mtime must be a number")
        raise ValueError("mtime must be a number")
    if not isinstance(file_hash, str) or len(file_hash) != 64:
        log.error("validation failed: hash must be a SHA-256 hex string")
        raise ValueError("hash must be a SHA-256 hex string")
    if any(character not in "0123456789abcdef" for character in file_hash.lower()):
        log.error("validation failed: hash must be a SHA-256 hex string")
        raise ValueError("hash must be a SHA-256 hex string")


def validate_version(version: int | None) -> None:
    if version is None:
        return
    if not isinstance(version, int) or version < 0:
        log.error("validation failed: version must be a non-negative integer")
        raise ValueError("version must be a non-negative integer")


def validate_filenames_list(filenames: list[str]) -> None:
    if not isinstance(filenames, list):
        log.error("validation failed: filenames must be a list")
        raise ValueError("filenames must be a list")
    for filename in filenames:
        validate_filename(filename)
