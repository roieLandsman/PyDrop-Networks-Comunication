# Server Storage Folder Instructions

This folder is reserved for the server-owned synchronized file copy and server metadata.

## Responsibilities

- Store files accepted through `UPLOAD` and `UPDATE`.
- Remove files after accepted `DELETE` messages.
- Keep metadata needed by the server, such as file size, modified time, hash, version, update id, and source client.

## Rules

- Do not store source code here.
- Do not commit generated runtime files unless they are intentional small samples for documentation.
- Server code should treat this folder as authoritative storage for the synchronized project data.
