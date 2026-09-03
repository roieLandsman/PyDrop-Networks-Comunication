import json
from socket import socket
import struct
from server.constants import BUFFER_SIZE, HEADER_LENGTH_BYTES, MAX_HEADER_BYTES


def recv_exact(sock: socket, byte_count: int) -> bytes | None:
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
        raise ValueError("Header ended before declared size")
        
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Header is not valid UTF-8 JSON") from error
        
    if not isinstance(header, dict):
        raise ValueError("Header JSON must be an object")
    return header
    

def read_message(sock: socket) -> tuple:
    """Read one framed PyDrop message from a socket."""
    header_size_bytes = recv_exact(sock, HEADER_LENGTH_BYTES)
    if header_size_bytes is None:
        return None, None
        
    # read the header as big-endian unsigned 4 byte integer
    header_size = struct.unpack(">I", header_size_bytes)[0]
    if header_size > MAX_HEADER_BYTES:
        raise ValueError("JSON header is too large")
    header = decode_header(recv_exact(sock, header_size))
    try:
        payload_size = int(header.get("size", 0))
        assert payload_size >= 0, "Payload size must be a positive integer"
    except (TypeError, ValueError) as error:
        raise ValueError("Payload size must be a positive integer")

    payload = recv_exact(sock, payload_size) if payload_size else b""
    if payload is None:
        raise ValueError("Payload ended before declared size")
    return header, payload


def send_message(sock: socket, message_header: dict, payload: bytes = b"") -> None:
    """Send one framed PyDrop message through a socket."""
    message_header["size"] = len(payload)
    
    # turn the header to a proper JSON format
    header_bytes = json.dumps(message_header, separators=(",", ":")).encode("utf-8")
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise ValueError("JSON header is too large")
    # send all the data as big-endian unsigned 4 byte integer
    sock.sendall(struct.pack(">I", len(header_bytes)) + header_bytes + payload)


def ack(message: str, client_id: str  = None, metadata: dict  = None, content_type: str  = None) -> dict:
    response = {"action": "ACK",  "status": "ok", "message": message, "size": 0}
    if client_id is not None:
        response["client_id"] = client_id
    if metadata is not None:
        response["metadata"] = metadata
    if content_type is not None:
        response["content_type"] = content_type
    return response, b""


def ack_with_payload(message: str, document: dict) -> tuple:
    """Build an ACK response with a JSON payload body."""
    response, _ = ack(message, content_type="application/json")
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    return response, payload
    

def error(code: str, message: str) -> dict:
    """Build an ERROR response header."""
    return {
        "action": "ERROR",
        "code": code,
        "message": message,
        "size": 0,
    }
