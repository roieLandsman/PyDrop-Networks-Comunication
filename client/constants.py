from pathlib import Path

# Docker clients reach the server by network alias; local clients use localhost.
HOST = "pydrop-server" if Path("/.dockerenv").exists() else "127.0.0.1"
PORT = 5001
BUFFER_SIZE = 4096
HEADER_LENGTH_BYTES = 4
MAX_HEADER_BYTES = 65536
SYNC_FOLDER = Path(__file__).resolve().parent / "sync_folder"
STATE_FILE_NAME = ".pydrop_state.json"
SCAN_INTERVAL_SECONDS = 2.0
UPDATE_INTERVAL_SECONDS = 5.0
RECONNECT_DELAY_SECONDS = 3.0

ERROR_BAD_REQUEST = "BAD_REQUEST"
ERROR_INVALID_FILENAME = "INVALID_FILENAME"
