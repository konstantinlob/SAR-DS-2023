import logging
import select
import socket

from common.types import Address
from common.packer import pack, unpack
from common.message import Message


class SendReceive:
    """
    Represents the OS layer of group communication (see fig. 3.1)
    """

    def __init__(self, deliver_callback, addr: Address):
        self.address = addr
        self.deliver_callback = deliver_callback

        # Create a server socket to listen for incoming connections
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(addr)
        self.server_socket.listen(5)

        # Set the server socket to non-blocking mode
        self.server_socket.setblocking(False)

        # Keep track of active sockets
        self.sockets = [self.server_socket]

    def run(self):
        self.handle_sockets()


    def send(self, to: Address, message: Message):
        """
        Send a message or file to the Client

        :param to:
        :param message: Metadata inserted by the middleware to provide reliable communication
        :return:
        """

        sendreceive_meta = dict(
            origin=self.address
        )

        message.add_meta("sendreceive", sendreceive_meta)
        msg_dict = message.to_dict()
        packed_msg = pack(msg_dict)

        # create a new socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # connect to the target
            sock.connect(to)
            logging.debug(f"New connection to {to}")
            # send the whole message
            sock.sendall(packed_msg)
            logging.debug(f"Sent message {message}")
            # automatically close the socket
            logging.debug(f"Connection to {to} closed.")

    def receive(self, data):
        msg_dict = unpack(data)
        message = Message.from_dict(msg_dict)

        logging.debug(f"Received message: {message.to_dict()}")
        self.deliver_callback(message)

    def handle_sockets(self):
        readable, _, _ = select.select(self.sockets, [], [], 0)

        for sock in readable:
            if sock == self.server_socket:
                # Handle a new incoming connection
                client_socket, addr = self.server_socket.accept()

                logging.debug(f"New connection from {addr}")
                # Set the client socket to non-blocking mode
                client_socket.setblocking(False)
                self.sockets.append(client_socket)
            else:
                # Handle data from a connected client

                # TODO this is sus, what happens with longer messages?
                # Should we use blocking sockets here and just wait until the whole message arrives? How?
                data = sock.recv(1024)
                if not data:
                    # Remove the socket if the connection is closed
                    logging.debug(f"Connection from {sock.getpeername()} closed.")
                    self.sockets.remove(sock)
                    sock.close()
                else:
                    logging.debug(f"Received data: {data}")
                    self.receive(data)
