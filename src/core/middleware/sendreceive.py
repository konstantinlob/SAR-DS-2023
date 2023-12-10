import logging
import select
import socket

from core.address import Address
from core.commands import Command
from core.packer import pack, unpack


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

    def send(self, to: Address, command: Command, body, msg_meta=None, broadcast_meta=None):
        """
        Send a message or file to the Client

        :param to:
        :param command:
        :param body: Additional parameters for the command
        :param broadcast_meta: Metadata inserted by the middleware to provide reliable communication
        :return:
        """

        if not broadcast_meta: broadcast_meta = {}
        if not msg_meta: msg_meta = {}

        # assemble the dict and convert the Command enum to its value (packer does not understand enums)
        unpacked_message = dict(
            command=command.value,
            body=body,
            msg_meta = msg_meta,
            broadcast_meta=broadcast_meta
        )
        # pack this dict
        message = pack(unpacked_message)
        # replace the value representation with the Command enum name for easier displaying
        unpacked_message["command"] = command.name

        # create a new socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # connect to the target
            sock.connect((to.ip, to.port))
            logging.info(f"New connection to {to}")
            # send the whole message
            sock.sendall(message)
            logging.info(f"Sent message {unpacked_message}")
            # automatically close the socket
            logging.info(f"Connection to {to} closed.")

    def receive(self, data):
        message = unpack(data)
        message["command"] = Command(message["command"])

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

                # TODO this is sus, what happens with longer messages?
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
