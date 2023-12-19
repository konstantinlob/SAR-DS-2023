import logging
from pathlib import Path

from common.communication.ack_manager import AckManager
from common.message import Message, Topic, Command
from common.types import Address
from states import ClientState


class BaseClient:
    """
    Base client that provides methods for connecting to servers, authenticating and sending messages.
    It does nothing on its own.
    """

    servers: list[Address]
    _state: ClientState

    # the file watcher can create file update messages at any time, but they will only be sent out when the client is
    # ready for it
    outgoing_message_queue: list[Message]

    def __init__(self):
        self.state = ClientState.STARTED
        self.outgoing_message_queue = []
        self.comm = AckManager(self.route, ("localhost", 51000))  # TODO don't hardcode address

        logging.info("Client started")

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
        if not self.comm.is_awaiting_ack():
            try:
                msg = self.outgoing_message_queue.pop(0)
                self.comm.r_broadcast(self.servers, msg, expect_ack=True)
            except IndexError:
                pass

    def route(self, message: Message):
        raise NotImplementedError

    def send(self, message: Message):
        self.outgoing_message_queue.append(message)

    def connect(self, server: Address) -> None:
        if self.state != ClientState.STARTED:
            raise RuntimeError()

        self.servers = [server]

        # request connection to the server group
        message = Message(
            Topic.CLIENT,
            Command.KNOCK
        )

        self.state = ClientState.CONNECTING
        self.send(message)

        logging.info(f"Connecting to {server}")

    def auth(self, username: str, password: str) -> None:
        if self.state == ClientState.AUTHENTICATING:
            raise RuntimeError("Authentication is already in process")

        self.state = ClientState.AUTHENTICATING

        message = Message(
            Topic.CLIENT,
            Command.AUTH,
            params=dict(
                username=username,
                password=password
            )
        )
        self.send(message)

        logging.info(f"Requesting authentication as '{username}' / '{password}'")


class ActiveReplClient(BaseClient):
    """
    Client that accepts messages required to keep an Active Replication network running.
    """

    def route(self, message: Message):
        match message.topic:
            case Topic.CLIENT:
                match message.command:
                    case Command.AUTH_SUCCESS:
                        return self.handle_message_client_auth_success(message)
                    case Command.SET_SERVERS:
                        return self.handle_message_client_set_servers(message)
                    case Command.ADD_SERVER:
                        return self.handle_message_client_add_server(message)
        super().route(message)

    def handle_message_client_set_servers(self, message: Message):

        servers = [tuple(addr) for addr in message.params["servers"]]
        logging.info(f"Setting servers to {servers}")
        self.servers = servers

    def handle_message_client_auth_success(self, message: Message):
        if self.state != ClientState.AUTHENTICATING:
            raise RuntimeError("Unexpected authentication success message")

        success = message.params["success"]

        if success:
            self.state = ClientState.RUNNING
            logging.info("Login successful")
        else:
            raise RuntimeError("Invalid credentials")

    def handle_message_client_add_server(self, message: Message):
        new_server = tuple(message.params["server"])
        logging.info(f"`New server: {new_server}")
        self.servers.append(new_server)


from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, EVENT_TYPE_CREATED, EVENT_TYPE_DELETED, \
    EVENT_TYPE_MODIFIED, EVENT_TYPE_MOVED, EVENT_TYPE_OPENED, EVENT_TYPE_CLOSED

from os import path


class FolderEventHandler(FileSystemEventHandler):
    # absolute path to the watched folder on the local disk
    folder: Path

    def __init__(self, folder: Path, sender):
        super().__init__()
        self.folder = folder
        self.send_file_message = sender

    def _get_relative(self, file_path: Path) -> str:
        return path.join(
            self.folder.name,
            path.relpath(file_path, self.folder)
        )

    def on_any_event(self, event):
        """Handle all relevant file system events by sending message to the server

        :param event:
            The event object representing the file system event.
        :type event:
            :class:`FileSystemEvent`
        """

        # Ignore events that don't change the file
        if event.event_type in [EVENT_TYPE_OPENED, EVENT_TYPE_CLOSED]: return

        command_for_event = {
            EVENT_TYPE_CREATED: Command.CREATED,
            EVENT_TYPE_DELETED: Command.DELETED,
            EVENT_TYPE_MODIFIED: Command.MODIFIED,
            EVENT_TYPE_MOVED: Command.MOVED,
        }

        try:
            command = command_for_event[event.event_type]
        except KeyError:
            raise NotImplementedError(f"Unknown event type '{event.event_type}'")

        src_path = self._get_relative(event.src_path)

        params = dict(
            is_directory=event.is_directory,
            src_path=src_path
        )

        # if the file was moved, inlcude the new path
        if event.event_type == EVENT_TYPE_MOVED:
            params["dest_path"] = self._get_relative(event.dest_path)

        logging.info(f"Registered event '{event.event_type}' at path '{event.src_path}'")

        # if the file was modified, include the new content
        filepath = Path(event.src_path)
        if event.event_type == EVENT_TYPE_MODIFIED and not event.is_directory:
            try:
                params["new_content"] = filepath.read_bytes()
            except FileNotFoundError:
                logging.warning(f"FileNotFoundError while attempting to read '{event.src_path}'. "
                                f"Was the file deleted too quickly?")
                return

        self.send_file_message(command, params)


class FileServiceClient(ActiveReplClient):
    observers: set[Observer]

    def __init__(self):
        super().__init__()
        self.observers = set()

    def add_watched_folder(self, folder: Path):
        """
        Watch a folder for changes
        :param folder: absolute path to the folder
        :return:
        """

        observer = Observer()
        handler = FolderEventHandler(folder, self.send_file_message)
        self.observers.add(observer)
        observer.schedule(handler, folder, recursive=True)
        observer.start()

        logging.info(f"Watcher started for '{folder}'")
        self.send_file_message(Command.WATCHED, dict(path=folder.name))

    def send_file_message(self, command: Command, params: dict):
        message = Message(
            topic=Topic.FILE,
            command=command,
            params=params
        )
        self.send(message)
