"""Client-side PyDrop protocol framing helpers.

The client implementation must stay standalone and must not import server or
shared runtime modules.
"""

import json
import socket
import struct

from client.constants import BUFFER_SIZE, HEADER_LENGTH_BYTES, MAX_HEADER_BYTES
from log import log


def recv_exact(sock: socket.socket, byte_count: int) -> bytes | None:
    """Receive exactly byte_count bytes from a socket."""
    chunks = []
    remaining = byte_count
    while remaining > 0:
        chunk = sock.recv(min(BUFFER_SIZE, remaining))
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def decode_header(header_bytes: bytes | None) -> dict:
    """Decode JSON header bytes into a dictionary."""
    if header_bytes is None:
        log.error("protocol error: header ended before declared size")
        raise ValueError("Header ended before declared size")
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        log.error("protocol error: header is not valid UTF-8 JSON")
        raise ValueError("Header is not valid UTF-8 JSON") from error
    if not isinstance(header, dict):
        log.error("protocol error: header JSON must be an object")
        raise ValueError("Header JSON must be an object")
    return header


def read_message(sock: socket.socket) -> tuple | None:
    """Read one framed PyDrop message from a socket."""
    header_size_bytes = recv_exact(sock, HEADER_LENGTH_BYTES)
    if header_size_bytes is None:
        return None
    header_size = struct.unpack(">I", header_size_bytes)[0]
    if header_size > MAX_HEADER_BYTES:
        log.error("protocol error: JSON header is too large")
        raise ValueError("JSON header is too large")
    header = decode_header(recv_exact(sock, header_size))
    try:
        payload_size = int(header.get("size", 0))
    except (TypeError, ValueError) as error:
        log.error("protocol error: payload size must be an integer")
        raise ValueError("Payload size must be an integer") from error
    if payload_size < 0:
        log.error("protocol error: payload size must not be negative")
        raise ValueError("Payload size must not be negative")
    payload = recv_exact(sock, payload_size) if payload_size else b""
    if payload is None:
        log.error("protocol error: payload ended before declared size")
        raise ValueError("Payload ended before declared size")
    return header, payload


def send_message(sock: socket.socket, header: dict, payload: bytes = b"") -> None:
    """Send one framed PyDrop message through a socket."""
    message_header = dict(header)
    message_header["size"] = len(payload)
    header_bytes = json.dumps(message_header, separators=(",", ":")).encode("utf-8")
    if len(header_bytes) > MAX_HEADER_BYTES:
        log.error("protocol error: JSON header is too large")
        raise ValueError("JSON header is too large")
    sock.sendall(struct.pack(">I", len(header_bytes)) + header_bytes + payload)
