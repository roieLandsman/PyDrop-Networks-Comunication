# PyDrop Design Notes

The source project plan is `../plan.pdf`.

## Architecture

PyDrop uses a client-server architecture:

- The server stores the authoritative synchronized file copy and metadata.
- Each client watches a local folder and reports local changes.
- Clients periodically ask the server for changes made by other clients.
- The server and client each implement protocol and file helpers locally in their own folders.
- The server and client each keep their API request functions in one local file: `api/requests.py`.

## Synchronization Flow

1. A client scans its local folder at a fixed interval.
2. The client compares the new snapshot with its previous snapshot.
3. Added or modified files are sent to the server with file bytes.
4. Deleted files are reported to the server with a delete message.
5. The server updates storage and metadata for active files or deletions.
6. Other clients check the server snapshot and download or delete files locally.
7. Clients confirm applied deletions so the server can remove old tombstones.

## Protocol

See `../API.md` for the socket framing and message conventions. The convention is shared as documentation only; runtime code is not shared.

## Base Limitations

The base implementation intentionally excludes encryption, user accounts, full version history, GUI, compression, and recursive subfolder support. These can be added after the core synchronization path is reliable.

## Coding Rules

- Server code and client code are standalone.
- The server owns one source of truth for server-side sync state.
- The client owns one source of truth for client-side sync state.
- Keep scripts under 200 lines and functions under 20 lines.
- Every function needs a docstring.
- Use comments only when a line is complicated enough to need explanation.
