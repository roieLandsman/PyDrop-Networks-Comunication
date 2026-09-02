# PyDrop API Convention

This document defines the socket message convention between PyDrop servers and clients.

The server and client must each implement this convention inside their own folder. Do not create or import a shared runtime protocol package.

Each side has an `api/requests.py` file. That file contains one function for each unique request type:

- Client: request builder functions named `connect`, `list_files`, `upload`, `update`, `download`, `delete`, `delete_seen`, and `check_updates`.
- Server: request handler functions named `handle_connect`, `handle_list_files`, `handle_upload`, `handle_update`, `handle_download`, `handle_delete`, `handle_delete_seen`, and `handle_check_updates`.

## Transport

- Communication uses TCP sockets.
- Every message starts with a 4-byte unsigned big-endian integer.
- That integer is the length, in bytes, of the JSON header that follows.
- The JSON header is encoded as UTF-8.
- If the header declares a nonzero `size`, exactly that many binary payload bytes follow the header.

Message frame:

```text
4-byte header length | JSON header bytes | optional binary payload
```

## Header Fields

Common header fields:

- `action`: message type, such as `UPLOAD` or `ACK`.
- `client_id`: unique id for the client sending the message.
- `filename`: normalized relative file name when the action targets a file.
- `size`: payload size in bytes. Use `0` when there is no payload.
- `mtime`: last modified timestamp reported by the source file system.
- `hash`: SHA-256 content hash for file integrity checks.
- `version`: server-assigned file version number.
- `seen_by`: client ids that have already applied a deleted-file tombstone.
- `status`: optional result status for acknowledgements.
- `code`: machine-readable error code for `ERROR`.
- `message`: human-readable error or status text.

All file names must be relative paths or plain names accepted by the project. They must not escape the synchronized folder.

## Message Types

### CONNECT

Client announces itself to the server.

```json
{
  "action": "CONNECT",
  "client_id": "client-1",
  "size": 0
}
```

### LIST_FILES

Client asks for the server file list and versions.

```json
{
  "action": "LIST_FILES",
  "client_id": "client-1",
  "size": 0
}
```

Successful response metadata is sent as a JSON payload so the response header
stays small:

```json
{
  "action": "ACK",
  "status": "ok",
  "message": "File list returned",
  "content_type": "application/json",
  "size": 79
}
```

### UPLOAD

Client sends a new file. The file bytes are sent as the payload.

```json
{
  "action": "UPLOAD",
  "client_id": "client-1",
  "filename": "notes.txt",
  "size": 128,
  "mtime": 1798200000.0,
  "hash": "sha256-hex-value"
}
```

### UPDATE

Client sends a changed version of an existing file. The new file bytes are sent as the payload.
Before uploading, the client checks the server snapshot for a newer unseen
version. If one exists, it renames the local file to `${filename}.local`,
overwriting that backup if needed, then downloads the server version.

```json
{
  "action": "UPDATE",
  "client_id": "client-1",
  "filename": "notes.txt",
  "size": 256,
  "mtime": 1798200100.0,
  "hash": "sha256-hex-value",
  "version": 2
}
```

### DOWNLOAD

Client asks for the latest server copy of a file.

```json
{
  "action": "DOWNLOAD",
  "client_id": "client-2",
  "filename": "notes.txt",
  "size": 0
}
```

### DELETE

Client tells the server that a file was deleted locally.

```json
{
  "action": "DELETE",
  "client_id": "client-1",
  "filename": "notes.txt",
  "size": 0
}
```

### CHECK_UPDATES

Client asks for the current server snapshot and deleted-file tombstones it has not seen.

```json
{
  "action": "CHECK_UPDATES",
  "client_id": "client-2",
  "size": 0
}
```

Successful response header:

```json
{
  "action": "ACK",
  "status": "ok",
  "message": "Snapshot returned",
  "content_type": "application/json",
  "size": 257
}
```

Successful response payload:

```json
{
  "files": {
    "notes.txt": {
      "filename": "notes.txt",
      "size": 128,
      "mtime": 1798200000.0,
      "hash": "sha256-hex-value",
      "version": 2,
      "origin_client": "client-1"
    }
  },
  "deleted": {
    "old.txt": {
      "filename": "old.txt",
      "mtime": 1798200200.0,
      "version": 3,
      "origin_client": "client-1",
      "seen_by": ["client-1"]
    }
  }
}
```

### DELETE_SEEN

Client confirms that it applied one or more deleted-file tombstones.

```json
{
  "action": "DELETE_SEEN",
  "client_id": "client-2",
  "filenames": ["old.txt"],
  "size": 0
}
```

### ACK

Server confirms that an operation succeeded.

```json
{
  "action": "ACK",
  "status": "ok",
  "message": "Upload accepted",
  "version": 3,
  "size": 0
}
```

### ERROR

Server or client reports a failed operation.

```json
{
  "action": "ERROR",
  "code": "FILE_NOT_FOUND",
  "message": "The requested file does not exist",
  "size": 0
}
```

## Error Convention

- `code` is stable and machine-readable.
- `message` is readable by humans and useful in logs.
- Receivers should log errors and avoid crashing on malformed or unsupported messages.

Suggested error codes:

- `BAD_REQUEST`
- `UNKNOWN_ACTION`
- `FILE_NOT_FOUND`
- `INVALID_FILENAME`
- `HASH_MISMATCH`
- `PAYLOAD_SIZE_MISMATCH`
- `SERVER_ERROR`

## Integrity Convention

For file transfers, the receiver computes the SHA-256 hash of the payload and compares it with the header `hash`. A mismatch should return `ERROR` with `HASH_MISMATCH`.

## Version Convention

The server is the source of truth for file versions. If two clients update the same file close together, the base implementation accepts updates in server receive order and assigns increasing versions.
