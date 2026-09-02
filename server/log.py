"""Server-side logging helpers for PyDrop."""

import logging
import sys


class Logger(logging.Logger):
    """Log server actions and client request traffic."""

    def __init__(self) -> None:
        """Create a console logger for server messages."""
        super().__init__("pydrop-server")
        self.setLevel(logging.INFO)
        self.add_stream_handler()

    def add_stream_handler(self) -> None:
        """Attach one stdout handler if none exists."""
        if self.handlers:
            return
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        self.addHandler(handler)

    def action(self, message: str) -> None:
        """Log an important server action."""
        self.info(f"[server] {message}")

    def received(
        self, request_name: str, client_name: str, ip_address: str
    ) -> None:
        """Log an incoming request from a client."""
        self.info(
            f"[received] {request_name} from ({client_name}, {ip_address})"
        )

    def sent(self, request_name: str, client_name: str, ip_address: str) -> None:
        """Log an outgoing response to a client."""
        self.info(f"[sent] {request_name} to ({client_name}, {ip_address})")


log = Logger()
