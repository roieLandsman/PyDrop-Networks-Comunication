"""Folder snapshot and local change detection for PyDrop clients."""

from pathlib import Path

from client.file_utils import clean_filename, file_metadata


def scan_folder(folder: Path) -> dict:
    """Return metadata for safe plain files directly inside folder."""
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = {}
    for path in folder.iterdir():
        if path.is_file() and is_safe_file(path.name):
            snapshot[path.name] = file_metadata(path)
    return snapshot


def is_safe_file(filename: str) -> bool:
    """Return True when filename is accepted by the API."""
    if filename.endswith(".local"):
        return False
    try:
        clean_filename(filename)
    except ValueError:
        return False
    return True


def diff_snapshots(old_snapshot: dict, new_snapshot: dict) -> dict:
    """Return added, modified, and deleted filenames."""
    old_names = set(old_snapshot)
    new_names = set(new_snapshot)
    added = sorted(new_names - old_names)
    deleted = sorted(old_names - new_names)
    modified = sorted(changed_names(old_snapshot, new_snapshot))
    return {"added": added, "modified": modified, "deleted": deleted}


def changed_names(old_snapshot: dict, new_snapshot: dict) -> list[str]:
    """Return names whose content hash changed."""
    names = set(old_snapshot).intersection(new_snapshot)
    return [
        name for name in names
        if old_snapshot[name].get("hash") != new_snapshot[name].get("hash")
    ]
