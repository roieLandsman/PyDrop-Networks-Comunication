"""Send invalid requests over TCP to an isolated instance of the real handler."""

import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from client.protocol import read_message, send_message
from log import log
from server.client_handler import Server, client_handler
from server.file_utils import sha256_bytes


class InvalidRequestsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="pydrop-tests-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.storage = self.root / "storage"
        self.storage.mkdir()
        self.metadata_file = self.root / "metadata.json"
        for target, value in (
            ("server.client_handler.METADATA_FILE", self.metadata_file),
            ("server.file_utils.STORAGE_DIR", self.storage),
        ):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        logging_patch = patch.object(log, "disabled", True)
        logging_patch.start()
        self.addCleanup(logging_patch.stop)

        self.server = Server()
        self.client_id = "negative-test-client"
        self.handler_errors = []
        with socket.create_server(("127.0.0.1", 0)) as listener:
            self.sock = socket.create_connection(listener.getsockname(), timeout=5)
            self.addCleanup(self.sock.close)
            self.server_sock, address = listener.accept()
        self.server_sock.settimeout(5)
        self.addCleanup(self.server_sock.close)

        def serve():
            try:
                client_handler(self.server_sock, address, self.server)
            except Exception as exception:
                self.handler_errors.append(exception)

        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_handler)
        header, payload = self.exchange({"action": "CONNECT"})
        self.assert_ack(header)
        self.assertEqual(payload, b"")

    def stop_handler(self):
        self.sock.close()
        self.thread.join(timeout=6)
        self.assertFalse(self.thread.is_alive(), "Server handler did not stop")
        self.assertEqual(self.handler_errors, [], "Server handler crashed")

    def exchange(self, request, payload=b""):
        # Bypass client.api.requests: its validation would reject bad filenames
        # locally, before the server gets a chance to validate them.
        request = {"client_id": self.client_id, **request, "size": len(payload)}
        show_messages = os.environ.get("PYDROP_SHOW_MESSAGES") == "1"
        if show_messages:
            print("\nSEND " + json.dumps(request, ensure_ascii=False), flush=True)
        send_message(self.sock, request, payload)
        response = read_message(self.sock)
        self.assertIsNotNone(response, "Server closed the connection")
        if show_messages:
            print("RECV " + json.dumps(response[0], ensure_ascii=False), flush=True)
        return response

    def file_request(self, action, filename, payload, version=None):
        request = {
            "action": action,
            "filename": filename,
            "mtime": 1700000000.0,
            "hash": sha256_bytes(payload),
        }
        if version is not None:
            request["version"] = version
        return request

    def assert_ack(self, header):
        self.assertEqual(header["action"], "ACK", header)
        self.assertEqual(header["status"], "ok", header)

    def assert_error(self, response, code):
        header, payload = response
        self.assertEqual(header["action"], "ERROR", header)
        self.assertEqual(header["code"], code, header)
        self.assertEqual(header["size"], 0)
        self.assertEqual(payload, b"")

    def disk_state(self):
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

    def assert_connection_usable(self):
        header, payload = self.exchange({"action": "CHECK_UPDATES"})
        self.assert_ack(header)
        self.assertEqual(json.loads(payload), self.server.snapshot_for_client(self.client_id))

    def test_stale_update(self):
        filename = "versioned.txt"
        first = b"original content"
        header, _ = self.exchange(self.file_request("UPLOAD", filename, first), first)
        self.assert_ack(header)
        self.assertEqual(header["metadata"]["version"], 1)

        current = b"current content"
        header, _ = self.exchange(self.file_request("UPDATE", filename, current, 1), current)
        self.assert_ack(header)
        self.assertEqual(header["metadata"]["version"], 2)
        metadata = header["metadata"]
        before = self.disk_state()

        stale = b"this must not overwrite the current content"
        response = self.exchange(self.file_request("UPDATE", filename, stale, 1), stale)
        self.assert_error(response, "STALE_VERSION")
        self.assertEqual(self.disk_state(), before)

        header, payload = self.exchange({"action": "DOWNLOAD", "filename": filename})
        self.assert_ack(header)
        self.assertEqual(payload, current)
        self.assertEqual(header["metadata"], metadata)

        # A valid update on the same connection still succeeds after rejection.
        latest = b"valid update after rejection"
        header, _ = self.exchange(self.file_request("UPDATE", filename, latest, 2), latest)
        self.assert_ack(header)
        self.assertEqual(header["metadata"]["version"], 3)
        self.assertEqual((self.storage / filename).read_bytes(), latest)

    def test_invalid_filename(self):
        payload = b"must not be written"
        invalid_names = (
            None,
            "",
            123,
            ".",
            "..",
            "../escape.txt",
            "subdir/file.txt",
            "..\\escape.txt",
            "subdir\\file.txt",
            str(self.root / "absolute.txt"),
        )
        for action in ("UPLOAD", "UPDATE"):
            for filename in invalid_names:
                with self.subTest(action=action, filename=filename):
                    before = self.disk_state()
                    request = self.file_request(action, filename, payload, version=0)
                    self.assert_error(self.exchange(request, payload), "INVALID_FILENAME")
                    self.assertEqual(self.disk_state(), before)
                    self.assertEqual(self.server.metadata["files"], {})
                    self.assertEqual(self.server.metadata["deleted"], {})
                    self.assert_connection_usable()

    def test_unsupported_action(self):
        before = self.disk_state()
        self.assert_error(self.exchange({"action": "RENAME"}), "UNKNOWN_ACTION")
        self.assertEqual(self.disk_state(), before)
        self.assert_connection_usable()


if __name__ == "__main__":
    unittest.main(verbosity=2)
