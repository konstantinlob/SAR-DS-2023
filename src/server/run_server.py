import logging

from core.address import Address
from core.constants import SERVER_HOST as HOST, SERVER_PORT as PORT
from server import FileServer

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    server = FileServer(Address(HOST, PORT))
    while True:
        server.comm.handle_sockets()
