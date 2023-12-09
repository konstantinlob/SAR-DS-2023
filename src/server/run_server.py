import socket
import socketserver

from core.constants import SERVER_HOST as HOST, SERVER_PORT as PORT
from core.network import get_network_identifier
from server import FileServer
from core.utils.address import Address

if __name__ == '__main__':
    server = FileServer(Address(HOST, PORT))
    while True:
        server.comm.handle_sockets()
