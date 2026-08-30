# Server Folder Instructions

This folder hosts the central PyDrop server implementation.

## Responsibilities

- Open a TCP socket and listen for client connections.
- Support multiple clients concurrently, initially with one thread or handler per client.
- Decode and validate protocol messages from clients.
- Handle `CONNECT`, `LIST_FILES`, `UPLOAD`, `UPDATE`, `DOWNLOAD`, `DELETE`, and `CHECK_UPDATES`.
- Maintain server-side metadata for synchronized files.
- Store the authoritative copy of synchronized files under `server/storage/`.
- Send `ACK` or `ERROR` after each operation.
- Log connection lifecycle events, file operations, errors, and disconnects.
- Own all server-side protocol framing, constants, file hashing, and path validation code.
- Keep server request handling API functions in `server/api/requests.py`.

## Expected Files

- `server.py`: server entry point and listening loop.
- `client_handler.py`: per-client request handling logic.
- `protocol.py`: server-side implementation of the TCP framing convention.
- `file_utils.py`: server-side file hashing, metadata, and safe path helpers.
- `constants.py`: server-side defaults, message names, and storage paths.
- `api/requests.py`: the single server API file, with one handler function for each unique request type.
- `storage/`: runtime storage and metadata for synchronized files.

Do not put client-side scanning logic here. Do not import runtime code from `client/` or from any shared project package.

## API Folder Rule

The `api/` folder must contain exactly one source file: `requests.py`. Add one public function for each unique request accepted by the server. Do not split request handlers across multiple files.

## Server Source Of Truth

The server must keep one authoritative server-side state owner for file metadata, versions, update ids, and storage paths. Other server modules may ask that owner for data or updates, but they must not keep independent long-lived copies of the same mutable state.

## Code Conventions

- Do not use `from __future__ import annotations`.
- Keep code simple, straightforward, and low-overhead.
- Every function must have a docstring.
- Add a one-line comment before any complicated line.
- Keep each Python script at 200 lines or fewer.
- Keep each function at 20 lines or fewer.
