# Client Folder Instructions

This folder hosts the PyDrop client implementation.

## Responsibilities

- Connect to the server through a TCP socket.
- Watch the configured local sync folder by polling snapshots.
- Detect added, modified, and deleted files.
- Send `UPLOAD`, `UPDATE`, and `DELETE` messages for local changes.
- Periodically send `CHECK_UPDATES` and download remote changes.
- Write server-provided files into `client/sync_folder/`.
- Avoid treating server-applied updates as new local user changes.
- Handle basic disconnects, reconnects, errors, and logs.
- Own all client-side protocol framing, constants, file hashing, and path validation code.
- Keep client request builder API functions in `client/api/requests.py`.

## Expected Files

- `client.py`: client entry point and sync loop orchestration.
- `folder_scanner.py`: local folder snapshot and change detection.
- `protocol.py`: client-side implementation of the TCP framing convention.
- `file_utils.py`: client-side file hashing, metadata, and safe path helpers.
- `constants.py`: client-side defaults, message names, and sync folder paths.
- `api/requests.py`: the single client API file, with one builder function for each unique request type.
- `sync_folder/`: default local folder for sample/runtime synchronization.

Do not import runtime code from `server/` or from any shared project package.

## API Folder Rule

The `api/` folder must contain exactly one source file: `requests.py`. Add one public function for each unique request sent by the client. Do not split request builders across multiple files.

## Client Source Of Truth

The client must keep one authoritative client-side state owner for local snapshots, last seen server update id, ignored server-applied changes, and client configuration. Other client modules may ask that owner for data or updates, but they must not keep independent long-lived copies of the same mutable state.

## Code Conventions

- Do not use `from __future__ import annotations`.
- Keep code simple, straightforward, and low-overhead.
- Every function must have a docstring.
- Add a one-line comment before any complicated line.
- Keep each Python script at 200 lines or fewer.
- Keep each function at 20 lines or fewer.
