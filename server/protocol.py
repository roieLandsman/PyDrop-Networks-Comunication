"""Server-side PyDrop protocol framing helpers.

The server implementation must stay standalone and must not import client or
shared runtime modules.
"""

import json
import struct

from server.constants import BUFFER_SIZE, HEADER_LENGTH_BYTES, MAX_HEADER_BYTES


def recv_exact(sock, byte_count):
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


def read_message(sock):
    """Read one framed PyDrop message from a socket."""
    header_size_bytes = recv_exact(sock, HEADER_LENGTH_BYTES)
    if header_size_bytes is None:
        return None
    header_size = struct.unpack(">I", header_size_bytes)[0]
    if header_size > MAX_HEADER_BYTES:
        raise ValueError("JSON header is too large")
    header = decode_header(recv_exact(sock, header_size))
    try:
        payload_size = int(header.get("size", 0))
    except (TypeError, ValueError) as error:
        raise ValueError("Payload size must be an integer") from error
    if payload_size < 0:
        raise ValueError("Payload size must not be negative")
    payload = recv_exact(sock, payload_size) if payload_size else b""
    if payload is None:
        raise ValueError("Payload ended before declared size")
    return header, payload


def decode_header(header_bytes):
    """Decode JSON header bytes into a dictionary."""
    if header_bytes is None:
        raise ValueError("Header ended before declared size")
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Header is not valid UTF-8 JSON") from error
    if not isinstance(header, dict):
        raise ValueError("Header JSON must be an object")
    return header


def send_message(sock, header, payload=b""):
    """Send one framed PyDrop message through a socket."""
    message_header = dict(header)
    message_header["size"] = len(payload)
    header_bytes = json.dumps(message_header, separators=(",", ":")).encode("utf-8")
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise ValueError("JSON header is too large")
    sock.sendall(struct.pack(">I", len(header_bytes)) + header_bytes + payload)


def ack(message, **extra_fields):
    """Build an ACK response header."""
    response = {
        "action": "ACK",
        "status": "ok",
        "message": message,
        "size": 0,
    }
    response.update(extra_fields)
    response["action"] = "ACK"
    response["status"] = "ok"
    response["message"] = message
    response["size"] = 0
    return response


def error(code, message):
    """Build an ERROR response header."""
    return {
        "action": "ERROR",
        "code": code,
        "message": message,
        "size": 0,
    }
