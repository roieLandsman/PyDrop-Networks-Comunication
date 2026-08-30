# PyDrop

PyDrop is a Python client-server file synchronization project. A central server stores the synchronized copy of files, and multiple clients keep local folders synchronized through a custom TCP socket protocol.

## Runtime Components

- Server that accepts multiple concurrent clients.
- Client that scans a local sync folder for file additions, changes, and deletions.
- Standalone server protocol/file utility modules.
- Standalone client protocol/file utility modules.
- Single-file API modules with one function per unique request.

## Base Requirements

- Python 3.11 or newer is recommended.
- No third-party runtime dependencies are required for the base implementation.

## Docker Usage

Run the server in one terminal. Logs print in that terminal.

```bash
build/start_server.sh
```

Run a client in another terminal. Logs print in that terminal.

```bash
build/start_client.sh client1
```

Open a shell inside that running client container's sync folder.

```bash
build/open_client_sync.sh client1
```

From that shell, create files to test synchronization.

```bash
echo "hello" > hello.txt
```

Start a second client by choosing another id.

```bash
build/start_client.sh client2
```

## Local Usage

Run the server:

```bash
python -m server.server
```

Run a client:

```bash
python -m client.client
```

The final command-line arguments and configuration files will be defined during implementation.
