"""Folder snapshot and local change detection for PyDrop clients."""

from pathlib import Path

from client.file_utils import file_metadata
from log import log
from client.validation import validate_filename


def changed_names(old_snapshot: dict, new_snapshot: dict) -> list[str]:
    """Return names whose content hash changed."""
    names = set(old_snapshot).intersection(new_snapshot)
    return [
        name for name in names
        if old_snapshot[name].get("hash") != new_snapshot[name].get("hash")
    ]


def diff_snapshots(old_snapshot: dict, new_snapshot: dict) -> dict:
    """Return added, modified, and deleted filenames."""
    old_names = set(old_snapshot)
    new_names = set(new_snapshot)
    added = sorted(new_names - old_names)
    deleted = sorted(old_names - new_names)
    modified = sorted(changed_names(old_snapshot, new_snapshot))
    return {"added": added, "modified": modified, "deleted": deleted}


def scan_folder(folder: Path) -> dict:
    """Return metadata for safe plain files directly inside folder."""
    snapshot = {}
    for path in folder.iterdir():
        if not path.is_file() or path.name.endswith(".local"):
            continue
        try:
            validate_filename(path.name)
        except ValueError as error:
            log.error(f"skipped invalid local filename {path.name}: {error}")
            continue
        snapshot[path.name] = file_metadata(path)
    return snapshot
