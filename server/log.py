"""Server-side logging helpers for PyDrop."""

import logging
import sys


class Logger(logging.Logger):
    """Log server actions and client request traffic."""

    def __init__(self):
        """Create a console logger for server messages."""
        super().__init__("pydrop-server")
        self.setLevel(logging.INFO)
        self.add_stream_handler()

    def add_stream_handler(self):
        """Attach one stdout handler if none exists."""
        if self.handlers:
            return
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.addHandler(handler)

    def action(self, message):
        """Log an important server action."""
        self.info(f"[server] {message}")

    def received(self, request_name, client_name, ip_address):
        """Log an incoming request from a client."""
        self.info(
            f"[received] {request_name} from ({client_name}, {ip_address})"
        )

    def sent(self, request_name, client_name, ip_address):
        """Log an outgoing response to a client."""
        self.info(f"[sent] {request_name} to ({client_name}, {ip_address})")


log = Logger()
