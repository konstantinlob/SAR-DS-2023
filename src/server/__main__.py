import os
import sys; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # noqa
import socketserver
from core.constants import SERVER_HOST as HOST, SERVER_PORT as PORT

WATCHED_DIRECTORIES_PATH = "../watched"
SPACE_MARGIN = 50 * 1 << 20  # 50 MiB
USERS = ("anonymous", "sar", "sza", "konstantin")
PASSWORDS = ("", "sar", "sza", "")
# TCP/UDP range ports open: 50000 - 50200

class ConnectionHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        print(f"New Request from {self.client_address}")
        self.do_handshake()
        self.handle_requests()

    def do_handshake(self):
        pass

    def handle_requests(self):
        while True:
            message = self.request.recv(100)
            print(f"Got Message: {message.decode()!r}")
            self.wfile.write(message)


if __name__ == '__main__':
    with socketserver.ForkingTCPServer((HOST, PORT), RequestHandlerClass=ConnectionHandler) as server:
        server.serve_forever()
