import logging
from enum import Enum

from common.communication.ack_manager import AckManager
from common.message import Message, Topic, Command
from common.types import Address


class ServerState(Enum):
    # server has just started
    STARTED = 0,
    # server has requested connection to the group
    CONNECTING = 1
    # server has received server and client details and is attempting to introduce itself to other nodes
    JOINING = 2,
    # server has joined server group and is registered with clients, running normally
    RUNNING = 3


class Server:
    servers: list[tuple[str, int]]
    clients: dict[tuple[str, int], bool]
    state: ServerState
    address: Address

    def __init__(self, address: Address):
        self.servers: list[Address] = [address]
        # collection of connected clients and ther authentication status
        self.clients: dict[Address, bool] = {}

        self.comm = AckManager(self.route, address)

        # the first server has no server group or clients to connect to
        self._state = ServerState.RUNNING
        self.address = address

    @property
    def state(self) -> ServerState:
        return self._state

    @state.setter
    def state(self, state):
        logging.info(f"State changed to {state}")
        self._state = state

    def run(self):
        self.comm.run()

    def route(self, message: Message):
        match message.topic:
            case Topic.CLIENT:
                match message.command:
                    case Command.KNOCK:
                        return self.handle_message_client_knock(message)
                    case Command.AUTH:
                        return self.handle_message_client_auth(message)
            case Topic.FILE:
                match message.command:
                    case Command.EXAMPLE:
                        return self.handle_message_file_example(message)
            case Topic.REPLICATION:
                match message.command:
                    case Command.CONNECT:
                        return self.handle_message_replication_connect(message)
                    case Command.ADD_SERVER:
                        return self.handle_message_replication_add_server(message)
        raise NotImplementedError(f"Command {message.topic.value}.{message.command.value} is not implemented")

    def handle_message_client_knock(self, message: Message):
        client = message.get_origin()
        logging.info(f"Client {client} knocked")
        message = Message(
            topic=Topic.CLIENT,
            command=Command.SET_SERVERS,
            params=dict(
                servers=self.servers
            )
        )
        self.comm.r_broadcast({client}, message)

    def handle_message_client_auth(self, message: Message):
        client = message.get_origin()

        username = message.params["username"]
        password = message.params["password"]

        logging.info(f"Client {client} is attempting to authenticate with credentials '{username}' / '{password}'")

        success = True  # TODO actually check credentials

        self.clients[client] = success

        reply = Message(
            topic=Topic.CLIENT,
            command=Command.AUTH_SUCCESS,
            params=dict(
                success=success
            )
        )

        self.comm.acknowledge_with_message(reply, message)

    def handle_message_file_example(self, message: Message):
        print(f"Received greeting from client: {message.params['example']}")
        self.comm.acknowledge(message)

    def handle_message_replication_connect(self, message: Message):
        """
        Receive connection attempt from new server and inform it about existing clients and servers
        :param message:
        :return:
        """

        new_server = message.get_origin()

        logging.info(f"Connection request from new server {new_server}")

        reply = Message(
            topic=Topic.REPLICATION,
            command=Command.INITIALIZE,
            params=dict(
                servers=self.servers,
                clients={}  # TODO send dict/list of clients
            )
        )
        logging.info("Initializing new server")
        self.comm.r_broadcast({new_server}, reply)

    def handle_message_replication_add_server(self, message):
        new_server = tuple(message.params['server'])
        logging.info(f"Attaching new server {new_server} to group")
        self.servers.append(new_server)


class BackupServer(Server):
    def __init__(self, own_address: Address):
        super().__init__(own_address)

        self.state = ServerState.STARTED
        self.comm.deliver_callback = self.route

    def connect(self, leader: Address):
        if self.state != ServerState.STARTED:
            raise RuntimeError

        logging.info(f"Attempting to connect to server group at {leader}")

        message = Message(
            Topic.REPLICATION,
            Command.CONNECT
        )

        self.state = ServerState.CONNECTING
        self.comm.r_broadcast({leader}, message)

    def introduce(self):
        if self.state != ServerState.JOINING:
            raise RuntimeError

        logging.info(f"Joining server group")

        message = Message(
            topic=Topic.CLIENT,
            command=Command.ADD_SERVER,
            params=dict(
                server=self.address
            )
        )

        # introduce to clients
        for client in self.clients:
            # this is actually a broadcast, but running this as a reliable broadcast would imply that the clients connect to each other
            # we want to avoid this, so the message is sent individually to each client
            self.comm.r_broadcast({client}, message)

        # introduce to other servers
        message.topic = Topic.REPLICATION
        self.comm.r_broadcast(self.servers, message)

    def route(self, message: Message):
        match message.topic:
            case Topic.REPLICATION:
                match message.command:
                    case Command.INITIALIZE:
                        return self.handle_message_replication_initialize(message)
        super().route(message)

    def handle_message_replication_initialize(self, message: Message):
        if self.state != ServerState.CONNECTING:
            raise RuntimeError()

        self.servers = [tuple(server) for server in message.params['servers']]
        for addr, auth_status in message.params['clients'].items():
            self.clients[addr] = auth_status

        self.state = ServerState.JOINING
        self.introduce()
