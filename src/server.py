import logging
from sys import stdout

from flask import Request, make_response
from werkzeug.exceptions import BadRequestKeyError
from requests.exceptions import ConnectionError

import messages.client
from utils import Address

logging.basicConfig(stream=stdout, level=logging.INFO)


class ConnectedClient:
    address: Address
    is_authenticated: bool

    def __init__(self, addr: Address):
        self.address = addr
        self.is_authenticated = False


class Server:
    """
    Base class containing methods for all features a server must offer to the client
    """

    address: Address
    clients: dict[Address, ConnectedClient] = {}
    backup_servers: set[Address]

    def __init__(self, address: Address):
        self.address = address
        self.backup_servers = set()

    def run(self):
        pass

    @staticmethod
    def _addr_from_request(request: Request) -> Address:
        """
        The server may need to know the address of the client in order to send replies back to the client.

        If the request was sent directly by the client,
        the client specifies its listening port for replies with the `port` argument.

        If the request was forwarded by the primary server, the primary server adds the `client` argument to the request.
        This argument contains the client IP and its listening port.
        """

        if "client" in request.args:
            return Address.parse(request.args["client"])
        elif "port" in request.args:
            client_ip = request.remote_addr
            client_port = int(request.args["port"])
            return Address(client_ip, client_port)

    def client_init(self, client: Address):
        """
        Add a new client to the list of clients
        :param client: Address of the new client
        """
        logging.info(f"Added new client {client}")
        self.clients[client] = ConnectedClient(client)

    def authenticate_client(self, client_addr: Address, username: str, password: str):
        """
        Check if username/password combination is valid, and authenticate the client
        """

        def credentials_valid(username: str, password: str) -> bool:
            # TODO validate credentials
            return True

        client = self.clients[client_addr]
        if credentials_valid(username, password):
            client.is_authenticated = True
            logging.info(f"Authenticated {client_addr}")
        else:
            logging.info(f"Invalid authentication attempt from {client_addr}")

    def client_demo_message(self, message: str):
        """
        Prints the message received from the client.
        This is only used to demonstrate how message forwarding / replication works.
        :param message: The message from the client
        """
        print(f'Received demo message "{message}"')

    def handle_client_init(self, request: Request):
        self.client_init(self._addr_from_request(request))
        return "ACK"

    def handle_client_authenticate(self, request: Request):
        try:
            username = request.form["username"]
            password = request.form["password"]
        except BadRequestKeyError:
            return make_response("Username or password missing.", 400)

        addr = self._addr_from_request(request)

        try:
            self.authenticate_client(addr, username, password)
        except KeyError:
            return make_response("Client is unknown to server. Please initialize client first.", 401)

        return "ACK"

    def handle_client_demo_message(self, request: Request):
        message = request.form["message"]
        self.client_demo_message(message)
        return "ACK"

    def handle_replication_set_backup(self, request: Request):
        backups = Address.deserialize_set(request.form["backups"])
        logging.info(f"Received new set of backup servers: {set(str(server) for server in backups)}")
        self.backup_servers = backups
        return "ACK"


class PrimaryServer(Server):

    def __init__(self, address: Address):
        super().__init__(address)

    def forward_client_request(self, request: Request):
        """
        Forwards a client request to all backup servers.
        The `client` argument is also inserted here to show which client originally sent the request.
        """
        client = self._addr_from_request(request)
        endpoint = request.path
        data = dict(request.form)
        params = dict(request.args)

        if request.method != "POST":
            # There is no reason to forward anything but POST requests,
            # since the primary server can handle GET requests alone
            raise Exception

        # we may need to change the set of active backup servers during the following iteration in case a backup fails.
        # the actual set must not change during the iteration in Python.
        # therefore I create a working copy here.
        backup_servers = self.backup_servers.copy()

        for server in backup_servers:
            try:
                messages.post(server, endpoint, params=params, data=data, client=client)
            except ConnectionError:
                self.backup_failed(server)

    def backup_failed(self, backup_server: Address):
        """
        Mark a backup server as failed and inform other backups about it
        :param backup_server: The failed server
        """
        logging.warning(f"Backup server {backup_server} has failed")
        self.backup_servers.remove(backup_server)
        self.replication_share_backups()

    def handle_client_init(self, request: Request):
        self.forward_client_request(request)
        return super().handle_client_init(request)

    def handle_client_authenticate(self, request: Request):
        self.forward_client_request(request)
        return super().handle_client_authenticate(request)

    def handle_client_demo_message(self, request: Request):
        self.forward_client_request(request)
        return super().handle_client_demo_message(request)

    def replication_init_backup(self, backup_addr: Address):
        """
        Include a new backup server and reply with a list of all backup servers
        :param backup_addr: Address of the new backup server
        """
        logging.info(f"New backup server {backup_addr}")
        self.backup_servers.add(backup_addr)
        return self.backup_servers

    def handle_replication_init_backup(self, request: Request):
        new_backup_server = self._addr_from_request(request)
        backup_servers = self.replication_init_backup(new_backup_server)
        return Address.serialize_set(backup_servers)


class BackupServer(Server):
    primary_server: Address

    def __init__(self, address: Address, primary_server: Address):
        super().__init__(address)
        self.primary_server = primary_server
        self.backup_servers.add(self.address)

    def run(self):
        """
        Sign up with the primary server
        """
        logging.info("Registering as new backup server")
        r = messages.post(self.primary_server, "replication/init-backup", port=self.address.port)

        self.backup_servers = Address.deserialize_set(r.text)

        logging.info(
            f"Received set of backup servers: {set(str(server) for server in self.backup_servers)}")

        self.share_backups()
        logging.info("Shared new set of backup servers with all other backups")

    def share_backups(self):
        for server in self.backup_servers:
            if server != self.address:
                messages.post(server, "replication/set-backups",
                              data={"backups": Address.serialize_set(self.backup_servers)})
