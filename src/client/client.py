from common.types import Address
from common.message import Message, Topic, Command
from common.communication.ack_manager import AckManager
import logging
from enum import Enum

class ClientState(Enum):
    STARTED = 0,
    INITIALIZING = 1,
    AUTHENTICATING = 2,
    RUNNING = 3

class Client:
    servers: list[Address]
    _state: ClientState

    # the file watcher can create file update messages at any time, but they will only be sent out when the client is ready for it
    file_message_queue: list[Message]



    def __init__(self):
        self.state = ClientState.STARTED
        self.file_message_queue = []
        self.comm = AckManager(self.route, ("localhost", 51000))  # TODO don't hardcode address

    @property
    def state(self) -> ClientState:
        return self._state

    @state.setter
    def state(self, state):
        logging.info(f"State changed to {state}")
        self._state = state

    def run(self):
        self.comm.run()

        # send messages that are in the queue
        if self.state == ClientState.RUNNING:
            try:
                msg = self.file_message_queue.pop(0)
                self.comm.r_broadcast_with_ack(self.servers, msg)
            except IndexError:
                pass

    def route(self, message: Message):
        match message.topic:
            case Topic.CLIENT:
                match message.command:
                    case Command.AUTH_SUCCESS:
                        return self.handle_message_client_auth_success(message)
                    case Command.SET_SERVERS:
                        return self.handle_message_client_set_servers(message)
        raise NotImplementedError

    def connect(self, server: Address) -> None:
        if self.state != ClientState.STARTED:
            raise RuntimeError()

        # send JOIN message
        message = Message(
            Topic.CLIENT,
            Command.KNOCK
        )

        self.state = ClientState.INITIALIZING
        self.comm.r_broadcast({server}, message)

    def auth(self) -> None:
        if self.state == ClientState.AUTHENTICATING:
            raise RuntimeError("Authentication is already in process")

        self.state = ClientState.AUTHENTICATING

        message = Message(
            Topic.CLIENT,
            Command.AUTH,
            params=dict(
                username="username",
                password="password"
            )
        )
        self.comm.r_broadcast_with_ack(self.servers, message)

    def handle_message_client_set_servers(self, message: Message):

        servers = [tuple(addr) for addr in message.params["servers"]]
        logging.info(f"Setting servers to {servers}")
        self.servers = servers

        self.auth()

    def handle_message_client_auth_success(self, message: Message):
        if self.state != ClientState.AUTHENTICATING:
            raise RuntimeError("Unexpected authentication success message")

        success = message.params["success"]

        if success:
            self.state = ClientState.RUNNING
            logging.info("Login successful")
        else:
            raise RuntimeError("Invalid credentials")