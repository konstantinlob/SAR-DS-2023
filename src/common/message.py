from enum import Enum
from common.types import Address


class Topic(Enum):
    FILE = "file"
    CLIENT = "client"
    REPLICATION = "replication"


class Command(Enum):
    # FILE commands
    EXAMPLE = "example"

    # CLIENT commands
    KNOCK = "knock"
    AUTH = "auth"
    AUTH_SUCCESS = "auth_success"

    ACK = "ack"
    SET_SERVERS = "set_servers"
    ADD_SERVER = "add_server"

    # REPLICATION commands


class Message:
    topic: Topic
    command: Command
    params: dict
    meta: dict[dict]

    def __init__(self, topic: Topic, command: Command, params: dict = dict(), meta: dict = dict()) -> None:
        self.topic = topic
        self.command = command
        self.params = params
        self.meta = meta

    def add_meta(self, middleware_name: str, meta: dict) -> None:
        self.meta[middleware_name] = meta

    def to_dict(self) -> dict:
        # copy all normal message properties into the dict
        d = dict(
            topic=self.topic.value,
            command=self.command.value,
            params=self.params,
            meta=self.meta,
        )

        return d

    def get_origin(self) -> Address:
        return tuple(self.meta["sendreceive"]["origin"])

    @classmethod
    def from_dict(cls, msg_dict: dict):
        topic = Topic(msg_dict["topic"])
        command = Command(msg_dict["command"])
        params = msg_dict["params"]
        meta = msg_dict["meta"]

        message = cls(topic, command, params, meta)

        return message

