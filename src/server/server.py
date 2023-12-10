import logging
import os
import sys
from pathlib import Path
from enum import Enum, auto
from typing import Set

from core.address import Address
from core.commands import Command
from core.middleware.r_broadcast import RBroadcastMiddleware
from filehandler import FileHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # noqa

SPACE_MARGIN = 50 * 1 << 20  # 50 MiB
USERS = {
    "anonymous": "",
    "sar": "sar",
    "sza": "sza",
    "konstantin": ""
}


# TCP/UDP range ports open: 50000 - 50200

class ServerState(Enum):
    LISTENING = auto()
    AWAITING_BACKUP_ACK = auto()


class FileServer:
    comm: RBroadcastMiddleware
    filehandler: FileHandler

    servers: set[Address]
    state: ServerState
    message_awaiting_ack: dict
    pending_acks: int
    unhandled_msgs: list

    def __init__(self, addr: Address):
        self.comm = RBroadcastMiddleware(self.receive, addr)
        self.filehandler = FileHandler()

        self.servers = {addr}

        self.state = ServerState.LISTENING
        self.message_awaiting_ack = None
        self.pending_acks = 0
        self.unhandled_msgs = [] # TODO handle this queue

    def receive(self, message):
        """
        Receives a message and forwards it to the correct place.

        If a client message is received while the server is not listening to clients, the message is stored for later

        :param message:
        :return:
        """

        source = message["msg_meta"]["source"]
        command = message["command"]

        if self.state == ServerState.LISTENING:
            if source == "client":
                self.deliver_from_client(message)
            else:
                raise NotImplementedError
        if self.state == ServerState.AWAITING_BACKUP_ACK:
            if command == Command.REPLICATION_ACK and source == "server":
                self.pending_acks -= 1
                if not self.pending_acks:
                    self.state = ServerState.LISTENING
                    self.deliver_from_client(self.message_awaiting_ack)
            else:
                self.unhandled_msgs.append(message)

    def deliver_from_client(self, message):
        """
        Is called when a message was received from the client and the server is currently listening for client requests
        :param message:
        :return:
        """

        # broadcast to all backups and wait for ACK
        if len(self.servers) > 1:
            self.state = ServerState.AWAITING_BACKUP_ACK
            self.message_awaiting_ack = message
            self.pending_acks = len(self.servers) - 1
            self.comm.r_broadcast(self.servers, message["command"], message["body"])
        # if there are no backups, we can handle the message directly
        else:
            self.exec_command_from_client(message)

    def deliver_from_server(self, message):
        raise NotImplementedError

    def exec_command_from_client(self, message):
        command = message["command"]
        body = message["body"]
        client_ip, client_port = message["msg_meta"]["client"]
        message["msg_meta"]["client"] = Address(client_ip, client_port)

        print(f"Received command: {command!r}")
        print(f"Received body: {body!r}")

        match command:
            case Command.CREATED:
                self.filehandler.handle_client_file_created(**body)
            case Command.DELETED:
                self.filehandler.handle_client_file_deleted(**body)
            case Command.MOVED:
                self.filehandler.handle_client_file_moved(**body)
            case Command.MODIFIED:
                self.filehandler.handle_client_file_modified(**body)
            case Command.WATCHED:
                self.filehandler.handle_client_file_watched(**body)
            case Command.AUTH:
                self.handle_client_auth(message["msg_meta"], **body)
            case _:
                raise ValueError

    def handle_client_auth(self, msg_meta, username: str, password: str):
        client = msg_meta["client"]

        logging.debug(f"Login attempt as {username}/{password}")

        success = username in USERS.keys() and USERS[username] == password

        logging.debug(f"Login successful: {username}/{password}")

        self.comm.r_broadcast(
            {client},
            Command.AUTH,
            dict(success=success)
        )


class PrimaryServer(FileServer):
    pass


class BackupServer(FileServer):
    def __init__(self, addr: Address, backup_for: Address):
        self.primary = backup_for
        super().__init__(addr)
