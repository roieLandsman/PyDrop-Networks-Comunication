# PyDrop Project Instructions

PyDrop is a Python client-server file synchronization system based on the project plan in `plan.pdf`.

## Project Goal

Build a complete TCP socket based system where one central server synchronizes files between multiple clients. Each client watches a local folder, detects added, modified, and deleted files, sends those changes to the server, and periodically downloads updates made by other clients.

## Base Implementation Scope

- Use Python and the standard library first.
- Use TCP sockets for all server-client communication.
- Support one central server and at least two concurrent clients.
- Detect local changes by polling folder snapshots.
- Support text files, binary files, empty files, and files large enough to require multiple `recv` calls.
- Store file metadata such as name, size, modified time, content hash, version, update id, and origin client.
- Handle basic disconnects, reconnects, invalid messages, acknowledgements, and errors.
- Avoid infinite sync loops when a client applies an update received from the server.

## Out Of Scope For The Base Version

Encryption, user accounts, permissions, full version history, recursive subfolders, compression, GUI, and advanced conflict handling are optional extensions after the core sync flow works.

## Repository Layout

- `server/` hosts all server runtime code, including server protocol helpers, server constants, server file utilities, and server-owned storage.
- `client/` hosts all client runtime code, including client protocol helpers, client constants, client file utilities, the folder scanner, and the watched local sync folder.
- `docs/` hosts design notes, setup notes, diagrams, screenshots, and presentation/demo material.

Keep runtime/generated files out of source folders unless the folder is explicitly intended for runtime data, such as `server/storage/` or `client/sync_folder/`.

Do not create shared runtime code packages. Server and client implementations must remain standalone, with any duplicated protocol or file helper behavior implemented locally on each side.

## Code Conventions

- Do not use `from __future__ import annotations`.
- Keep all code simple and straightforward.
- Avoid overhead: do not add abstractions, frameworks, background services, or helpers unless they clearly simplify the current implementation.
- Every function must have documentation with a clear docstring.
- Every complicated line must have a one-line comment explaining why it is needed.
- Each Python script must be 200 lines or fewer.
- Each function must be 20 lines or fewer.
- Prefer explicit names and direct control flow over clever or compressed code.

## Source Of Truth Rules

- The client must have one client-side source of truth for sync state and client configuration.
- The server must have one server-side source of truth for file metadata, versions, and update history.
- Client code must not read or modify server state directly.
- Server code must not read or modify client state directly.
- Do not duplicate mutable state across modules unless one copy is a temporary local value derived from the source of truth.
