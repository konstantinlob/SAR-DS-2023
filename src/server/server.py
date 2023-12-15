from common.communication.ack_manager import AckManager
from common.message import Message, Topic, Command
from common.types import Address
import logging

class Server:
    def __init__(self):
        own_address = ("localhost", 50000)  # TODO don't hardcode address
        self.servers: list[Address] = [own_address]
        self.comm = AckManager(self.route, own_address)

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
        raise NotImplementedError

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

        reply = Message(
            topic=Topic.CLIENT,
            command=Command.AUTH_SUCCESS,
            params=dict(
                success=True # TODO check credentials
            )
        )

        self.comm.acknowledge_with_message(reply, message)

    def handle_message_file_example(self, message: Message):
        print(f"Received greeting from client: {message.params['example']}")
        self.comm.acknowledge(message)