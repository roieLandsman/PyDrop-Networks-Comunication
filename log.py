"""Shared logging helpers for PyDrop."""

import logging
import sys


class Logger(logging.Logger):
    """Log PyDrop actions, errors, and protocol traffic."""

    def __init__(self) -> None:
        """Create a console logger."""
        super().__init__("log")
        self.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        self.addHandler(handler)

    def info(self, message: str) -> None:
        """Log an important action."""
        super().info(f"[info] {message}")

    def error(self, message: str) -> None:
        """Log an error."""
        super().error(f"[ERROR] {message}")

    def received(self, request_name: str, src_name: str, ip_address: str) -> None:
        """Log an incoming request or response."""
        super().info(f"[received] {request_name} from ({src_name}, {ip_address})")

    def sent(self, request_name: str, dst_name: str, ip_address: str) -> None:
        """Log an outgoing request or response."""
        super().info(f"[sent] {request_name} to ({dst_name}, {ip_address})")


log = Logger()
