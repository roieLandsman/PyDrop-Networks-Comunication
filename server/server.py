import threading
from server.log import log
from server.client_handler import Server, client_handler
from server.constants import HOST, PORT, BACKLOG, STORAGE_DIR
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR


# Create and return a new server socket
def create_new_server_socket() -> socket:
    sock = socket(AF_INET, SOCK_STREAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(BACKLOG)
    log.action(f"connected to socket on {HOST}:{PORT}")
    return sock


# wait for new clients and allow them to connect to the server
def wait_and_accept_new_clients(sock: socket, server: Server) -> None:
    while True:
        client_socket, client_address = sock.accept()
        log.action(f"accepted connection from {client_address}")
        args = (client_socket, client_address, server)
        # daemon=True make sure all threads will close together with the main server process when it stops.
        # target: the function to run in the thread
        # args: the arguments to pass to the function
        thread = threading.Thread(target=client_handler, args=args, daemon=True)
        thread.start()
        log.action(f"started a thread for client {client_address}")

# Start the server
def start_server() -> None:   
    log.action("Server started")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    server = Server()

    # will automatically close the socket when exiting the with..as block.
    with create_new_server_socket() as sock:
        wait_and_accept_new_clients(sock, server)

# Run the server
def main() -> None:
    try:
      start_server()
    except KeyboardInterrupt:
        log.action("stopped by user")
    except Exception as e:
        print(e)

if __name__ == "__main__": 
    main()


  
