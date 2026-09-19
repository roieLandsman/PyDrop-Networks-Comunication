"""Client-side response readers for PyDrop API replies."""

import json

from log import log


def payload_json(header: dict, payload: bytes) -> dict:
    """Decode a JSON response payload."""
    if header.get("content_type") != "application/json":
        log.error("response error: payload is not JSON")
        raise RuntimeError("response payload is not JSON")
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        log.error("response error: payload is invalid JSON")
        raise RuntimeError("response payload is invalid JSON") from error
    if not isinstance(document, dict):
        log.error("response error: payload JSON must be an object")
        raise RuntimeError("response payload JSON must be an object")
    return document


def snapshot(header: dict, payload: bytes | None) -> dict:
    """Return CHECK_UPDATES files and deletions from a response."""
    document = payload_json(header, payload) if payload else header
    return {
        "files": document.get("files", {}),
        "deleted": document.get("deleted", {}),
    }
