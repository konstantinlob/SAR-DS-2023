import socket
import socketserver

from core.constants import SERVER_HOST as HOST, SERVER_PORT as PORT
from core.network import get_network_identifier
from server import ConnectionHandler

if __name__ == '__main__':
    with socketserver.ForkingTCPServer((HOST, PORT), RequestHandlerClass=ConnectionHandler) as server:
        print("Server is up")
        print(f"Connect client to {get_network_identifier(HOST)}:{PORT} / {socket.getfqdn(HOST)}:{PORT}")
        server.serve_forever()
