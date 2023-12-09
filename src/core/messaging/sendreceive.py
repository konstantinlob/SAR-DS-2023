from core.packer import pack, unpack
from core.utils.address import Address
import socket, select, logging


class SendReceiveMiddleware:
    """
    Represents the OS layer of group communication (see fig. 3.1)
    """

    def __init__(self, deliver_callback, addr: Address):
        self.deliver_callback = deliver_callback

        # Create a server socket to listen for incoming connections
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((addr.ip, addr.port))
        self.server_socket.listen(5)

        # Set the server socket to non-blocking mode
        self.server_socket.setblocking(0)

        # Keep track of active sockets
        self.sockets = [self.server_socket]

    def send(self, to: Address, command: str, body, meta=None):
        """
        Send a message or file to the Client

        :param to:
        :param command:
        :param body: Additional parameters for the command
        :param meta: Metadata inserted by the middleware to provide reliable communication
        :return:
        """

        if not meta: meta = {}

        message = pack(dict(
            command=command,
            body=body,
            meta=meta
        ))

        # create a new socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # connect to the target
            sock.connect((to.ip, to.port))
            # send the whole message
            sock.sendall(message)
            # automatically close the socket

    def receive(self, data):
        message = unpack(data)
        logging.info(f"Received message: {message}")
        self.deliver_callback(message)

    def handle_sockets(self):
        readable, _, _ = select.select(self.sockets, [], [])

        for sock in readable:
            if sock == self.server_socket:
                # Handle a new incoming connection
                client_socket, addr = self.server_socket.accept()

                logging.info(f"New connection from {addr}")
                # Set the client socket to non-blocking mode
                client_socket.setblocking(0)
                self.sockets.append(client_socket)
            else:
                # Handle data from a connected client

                #TODO this is sus, what happens for longer messages?
                # Should we use blocking sockets here and just wait until the whole message arrives? How?
                data = sock.recv(1024)
                if not data:
                    # Remove the socket if the connection is closed
                    logging.info(f"Connection from {sock.getpeername()} closed.")
                    self.sockets.remove(sock)
                    sock.close()
                else:
                    logging.debug(f"Received data: {data}")
                    self.receive(data)

