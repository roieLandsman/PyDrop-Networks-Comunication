"""PyDrop server entry point.

Implementation opens the TCP listener, accepts clients, and delegates each
connection to a client handler.
"""

import socket
import threading

from server.constants import HOST, PORT, BACKLOG, STORAGE_DIR
from server.client_handler import ServerState, handle_client
from server.log import log


def create_listener() -> socket.socket:
    """Create and return a configured listening socket."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((HOST, PORT))
    listener.listen(BACKLOG)
    log.action(f"listening on {HOST}:{PORT}")
    return listener


def accept_clients(listener, state):
    """Accept clients and run each connection in a daemon thread."""
    while True:
        client_sock, address = listener.accept()
        log.action(f"accepted connection from {address[0]}")
        thread = threading.Thread(
            target=handle_client,
            args=(client_sock, address, state),
            daemon=True,
        )
        thread.start()


def start_server():
    """Start the PyDrop server."""
    log.action("started")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    log.action(f"using storage folder {STORAGE_DIR}")
    state = ServerState()

    # will automatically close the socket when exiting the with..as block.
    with create_listener() as listener:
        accept_clients(listener, state)


def main():
    """Run the PyDrop server from the command line."""
    start_server()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.action("stopped")
