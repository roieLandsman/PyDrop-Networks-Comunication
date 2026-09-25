import threading
from log import log
from server.client_handler import Server, client_handler
from server.constants import HOST, PORT, BACKLOG, STORAGE_DIR
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR


def create_new_server_socket() -> socket:
    "create and return a new server socket"
    sock = socket(AF_INET, SOCK_STREAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(BACKLOG)
    log.info(f"connected to socket on {HOST}:{PORT}")
    return sock


def wait_and_accept_new_clients(sock: socket, server: Server) -> None:
    "wait for new clients and allow them to connect to the server"
    while True:
        client_socket, client_address = sock.accept()
        log.info(f"accepted connection from {client_address}")
        args = (client_socket, client_address, server)
        # daemon=True make sure all threads will close together with the main server process when it stops.
        # target: the function to run in the thread
        # args: the arguments to pass to the function
        thread = threading.Thread(target=client_handler, args=args, daemon=True)
        thread.start()
        log.info(f"started a thread for client {client_address}")


def start_server() -> None: 
    "start the server handler and socket" 
    log.info("Server started")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    server = Server()

    # will automatically close the socket when exiting the with..as block.
    with create_new_server_socket() as sock:
        wait_and_accept_new_clients(sock, server)


def main() -> None:
    "entrypoint for the server program"
    try:
      start_server()
    except KeyboardInterrupt:
        log.info("stopped by user")
    except Exception as e:
        log.error(f"server error: {e}")

if __name__ == "__main__": 
    main()


  
