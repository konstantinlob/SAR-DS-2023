import logging
from sys import stdout

from flask import Request, make_response
from werkzeug.exceptions import BadRequestKeyError

import messages.client
from stuff import Address

logging.basicConfig(stream=stdout, level=logging.INFO)


class ConnectedClient:
    address: Address
    is_authenticated: bool

    def __init__(self, addr: Address):
        self.address = addr
        self.is_authenticated = False


class Server:
    """
    Base class containing methods for all features a server must offer
    """

    address: Address
    clients: dict[Address, ConnectedClient] = {}

    def __init__(self, address: Address):
        self.address = address

    @staticmethod
    def _addr_from_request(request: Request) -> Address:

        if "client" in request.args:
            return Address.parse(request.args["client"])
        elif "port" in request.args:
            client_ip = request.remote_addr
            client_port = int(request.args["port"])
            return Address(client_ip, client_port)

    def client_init(self, client_addr: Address):
        """
        Add a new client to the list of clients
        :param client_addr:
        :return:
        """
        logging.info(f"Added new client {client_addr}")
        self.clients[client_addr] = ConnectedClient(client_addr)

    def authenticate_client(self, client_addr: Address, username: str, password: str):
        """
        Check if username/password combination is valid, and authenticate the client
        :param client_addr:
        :param username:
        :param password:
        :return:
        """

        def credentials_valid(username: str, password: str) -> bool:
            # TODO validate credentials
            return True

        client = self.clients[client_addr]
        if credentials_valid(username, password):
            client.is_authenticated = True
            logging.info(f"Authenticated {client}")
        else:
            logging.info(f"Invalid authentication attempt from {client}")

    def client_demo_message(self, message: str):
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


class PrimaryServer(Server):
    backup_servers: set[Address]

    def __init__(self, address: Address):
        super().__init__(address)
        self.backup_servers = set()
        
    def forward_client_request(self, request: Request):
        client = self._addr_from_request(request)
        endpoint = request.path
        data = dict(request.form)
        params = dict(request.args)

        for server in self.backup_servers:
            messages.post(server, endpoint, params=params, data=data, client=client)
        
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
        logging.info(f"New backup server {backup_addr}")
        self.backup_servers.add(backup_addr)
        self.replication_share_backups()

    def replication_share_backups(self):
        pass

    def handle_replication_init_backup(self, request: Request):
        new_backup_server = self._addr_from_request(request)
        self.replication_init_backup(new_backup_server)
        return "ACK"


class BackupServer(Server):
    primary_server: Address
    other_backup_servers: set[Address]

    def __init__(self, address: Address, primary_server: Address):
        super().__init__(address)
        self.primary_server = primary_server
        self.other_backup_servers = set()
        self.init()

    def init(self):
        logging.info("Registering as new backup server")
        r = messages.post(self.primary_server, "replication/init-backup", port=self.address.port)
        if r.status_code != 200:
            raise Exception
