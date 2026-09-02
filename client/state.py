"""Client-side source of truth for PyDrop sync state."""

from pathlib import Path

from client.file_utils import delete_file, write_file
from client.folder_scanner import diff_snapshots, scan_folder


class ClientState:
    """Own client configuration, snapshots, and sync state."""

    def __init__(self, client_id: str, folder: str | Path) -> None:
        """Create the single mutable client state owner."""
        self.client_id = client_id
        self.folder = Path(folder)
        self.snapshot = {}
        self.server_versions = {}
        self.last_update_check = 0.0

    def refresh_snapshot(self) -> dict:
        """Scan the folder and return local changes."""
        new_snapshot = scan_folder(self.folder)
        changes = diff_snapshots(self.snapshot, new_snapshot)
        return changes

    def load_snapshot(self) -> None:
        """Load the current folder snapshot without reporting changes."""
        self.snapshot = scan_folder(self.folder)

    def current_metadata(self, filename: str) -> dict | None:
        """Return current local metadata for one tracked file."""
        return scan_folder(self.folder).get(filename)

    def remember_synced_file(
        self, filename: str, metadata: dict, version: int
    ) -> None:
        """Mark one local file as accepted by the server."""
        self.snapshot[filename] = metadata
        self.remember_version(filename, version)

    def remember_synced_delete(self, filename: str, version: int) -> None:
        """Mark one local deletion as accepted by the server."""
        self.snapshot.pop(filename, None)
        self.remember_version(filename, version)

    def apply_download(
        self, filename: str, payload: bytes, metadata: dict
    ) -> None:
        """Write a downloaded file and update local state."""
        write_file(filename, payload, self.folder, metadata.get("mtime"))
        self.snapshot = scan_folder(self.folder)
        self.server_versions[filename] = int(metadata.get("version", 0))

    def apply_delete(self, filename: str) -> None:
        """Delete a remote tombstone locally and update local state."""
        delete_file(filename, self.folder)
        self.snapshot = scan_folder(self.folder)
        self.server_versions.pop(filename, None)

    def remember_version(self, filename: str, version: int) -> None:
        """Store the latest server version for a file."""
        self.server_versions[filename] = int(version)
