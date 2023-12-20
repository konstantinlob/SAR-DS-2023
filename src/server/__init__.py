import logging

from common.communication.ack_manager import AckManager
from common.message import Message, Topic, Command
from common.types import Address
from common.users import check_auth, AccessType
from server.states import ServerState


class BaseServer:
    servers: list[tuple[str, int]]
    clients: dict[tuple[str, int], AccessType]
    state: ServerState
    address: Address

    def __init__(self, address: Address):
        self.servers: list[Address] = [address]
        # collection of connected clients and their authentication status
        self.clients = {}

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
        raise NotImplementedError(f"Command {message.topic.name}.{message.command.name} is not implemented")

    def handle_message_client_knock(self, message: Message):
        client = message.get_origin()
        logging.info(f"Client {client} knocked")
        reply = Message(
            topic=Topic.CLIENT,
            command=Command.SET_SERVERS,
            params=dict(
                servers=self.servers
            )
        )
        self.comm.acknowledge_with_message(reply, message)

    def handle_message_client_auth(self, message: Message):
        client = message.get_origin()

        username = message.params["username"]
        password = message.params["password"]

        access_type = check_auth(username, password)

        logging.info(f"Client {client} is attempting to authenticate with credentials '{username}' / '{password}' "
                     f"--> {access_type}")

        self.clients[client] = access_type

        reply = Message(
            topic=Topic.CLIENT,
            command=Command.AUTH_SUCCESS,
            params=dict(
                success=bool(access_type)
            )
        )

        self.comm.acknowledge_with_message(reply, message)


class ActiveReplServer(BaseServer):

    def route(self, message: Message):
        match message.topic:
            case Topic.REPLICATION:
                match message.command:
                    case Command.CONNECT:
                        return self.handle_message_replication_connect(message)
                    case Command.ADD_SERVER:
                        return self.handle_message_replication_add_server(message)
        super().route(message)

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
                # packer has trouble unpacking the dict
                # so here the items are arranged in a list and re-ordered by the receiving end
                clients=[(addr, auth_status.value) for addr, auth_status in self.clients.items()]
            )
        )
        logging.info("Initializing new server")
        self.comm.r_broadcast({new_server}, reply)

    def handle_message_replication_add_server(self, message):
        new_server = tuple(message.params['server'])
        logging.info(f"Attaching new server {new_server} to group")
        self.servers.append(new_server)


from os.path import commonpath
from pathlib import Path


class FileServiceServer(ActiveReplServer):
    def __init__(self, address: Address, storage_dir: Path):
        super().__init__(address)

        if storage_dir.exists():
            if not storage_dir.is_dir():
                raise RuntimeError("Storage directory is not a directory")
        else:
            storage_dir.mkdir(parents=True, exist_ok=True)
            logging.info("Storage directory does not exist, creating new directory")

        self.files = storage_dir

    def route(self, message: Message):
        match message.topic:
            case Topic.FILE:
                match message.command:
                    case Command.EXAMPLE:
                        return self.handle_message_file_example(message)
                    case Command.WATCHED:
                        return self.handle_message_file_watched(message)
                    case Command.CREATED:
                        return self.handle_message_file_created(message)
                    case Command.DELETED:
                        return self.handle_message_file_deleted(message)
                    case Command.MODIFIED:
                        return self.handle_message_file_modified(message)
                    case Command.MOVED:
                        return self.handle_message_file_moved(message)
        super().route(message)

    def _local_path(self, path: str) -> Path:
        """Maps the folder name transmitted by the client to a folder on the local disk
        """
        real = (self.files / path).absolute()
        if commonpath([str(self.files), real]) != str(self.files):
            raise PermissionError("Bad path")
        return real

    def _enforce_authorization(self, message: Message, min_required_auth: AccessType = AccessType.AUTHORIZED) -> bool:
        client = tuple(message.meta["sendreceive"]["origin"])

        def send_error(error: str):
            error_msg = Message(topic=Topic.CLIENT, command=Command.ERROR, params={"error": error})
            self.comm.acknowledge_with_message(error_msg, message)

        if client not in self.clients.keys():
            send_error("Permission denied: Unknown client - Please authenticate first")
            return False
        elif self.clients[client].value < min_required_auth.value:
            send_error("Permission denied: This operation is not allowed for this user")
            return False
        else:
            return True

    def handle_message_file_example(self, message: Message):
        if not self._enforce_authorization(message, min_required_auth=AccessType.ANONYMOUS): return

        print(f"Received greeting from client: {message.params['example']}")
        self.comm.acknowledge(message)

    def handle_message_file_watched(self, message: Message):
        if not self._enforce_authorization(message): return

        src_path = self._local_path(message.params['path'])
        src_path.mkdir(parents=True, exist_ok=True)

        logging.info(f"Watching new path: {message.params['path']}")

        self.comm.acknowledge(message)

    def handle_message_file_created(self, message: Message):
        if not self._enforce_authorization(message): return

        src_path = self._local_path(message.params['src_path'])
        is_directory = message.params['is_directory']

        if is_directory:
            src_path.mkdir()
        else:
            src_path.touch()

        logging.info(f"File created: {message.params['src_path']}")

        self.comm.acknowledge(message)

    def handle_message_file_modified(self, message: Message):
        if not self._enforce_authorization(message): return

        src_path = self._local_path(message.params['src_path'])
        is_directory = message.params['is_directory']

        if is_directory:
            logging.info(f"Directory modified: {message.params['src_path']}")
        else:
            new_content = message.params['new_content']

            if new_content is not None:
                with open(src_path, 'wb') as file:
                    file.write(new_content)

            logging.info(f"File modified: {message.params['src_path']} (length of new content: {len(new_content)})")

        self.comm.acknowledge(message)

    def handle_message_file_moved(self, message: Message):
        if not self._enforce_authorization(message): return

        src_path = self._local_path(message.params['src_path'])
        dest_path = self._local_path(message.params['dest_path'])
        src_path.rename(dest_path)

        logging.info(f"File moved: {message.params['src_path']} -> {message.params['dest_path']}")

        self.comm.acknowledge(message)

    def handle_message_file_deleted(self, message: Message):
        if not self._enforce_authorization(message): return

        src_path = self._local_path(message.params['src_path'])
        is_directory = message.params['is_directory']
        if is_directory:
            src_path.rmdir()
        else:
            src_path.unlink()

        logging.info(f"{'Directory' if is_directory else 'File'} deleted: {message.params['src_path']}")

        self.comm.acknowledge(message)


class FileServiceBackupServer(FileServiceServer):
    def __init__(self, own_address: Address, storage_dir: Path):
        super().__init__(own_address, storage_dir)

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
            # this is actually a broadcast, but running this as a reliable broadcast would imply that the clients
            # connect to each other.
            # we want to avoid this, so the message is sent individually to each client
            self.comm.r_broadcast({client}, message)

        # introduce to other servers
        message.topic = Topic.REPLICATION
        self.comm.r_broadcast(self.servers, message)

        self.state = ServerState.RUNNING

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
        self.clients = {tuple(addr): AccessType(access_type) for addr, access_type in message.params['clients']}

        logging.info(
            f"Initialized with the following connections:\n\tServers: {self.servers}\n\tClients: {self.clients}")

        self.state = ServerState.JOINING
        self.introduce()
