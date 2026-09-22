import logging
import sys

class Logger(logging.Logger):
    def __init__(self) -> None:
        super().__init__("log")
        self.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        self.addHandler(handler)

    def info(self, message: str) -> None:
        super().info(f"[info] {message}")

    def error(self, message: str) -> None:
        super().error(f"[ERROR] {message}")

    def received(self, request_name: str, src_name: str, ip_address: str) -> None:
        super().info(f"[received] {request_name} from ({src_name}, {ip_address})")

    def sent(self, request_name: str, dst_name: str, ip_address: str) -> None:
        super().info(f"[sent] {request_name} to ({dst_name}, {ip_address})")


log = Logger()
