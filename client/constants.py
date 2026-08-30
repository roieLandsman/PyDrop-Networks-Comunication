"""Client-side PyDrop constants."""

import os
from pathlib import Path


HOST = os.environ.get("PYDROP_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("PYDROP_PORT", "5001"))
BUFFER_SIZE = 4096
HEADER_LENGTH_BYTES = 4
MAX_HEADER_BYTES = 65536
SYNC_FOLDER = Path(__file__).resolve().parent / "sync_folder"
SCAN_INTERVAL_SECONDS = 2.0
UPDATE_INTERVAL_SECONDS = 5.0
RECONNECT_DELAY_SECONDS = 3.0

ERROR_BAD_REQUEST = "BAD_REQUEST"
ERROR_INVALID_FILENAME = "INVALID_FILENAME"
