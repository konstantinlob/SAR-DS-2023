from enum import Enum, auto


class Command(Enum):

    # FILE MANAGEMENT
    CREATED = auto()
    DELETED = auto()
    MOVED = auto()
    MODIFIED = auto()
    WATCHED = auto()

    # CLIENT MANAGEMENT

    # authenticate as new client
    AUTH = auto()

    # REPLICATION management

    # register a new replication server
    REPLICATION_JOIN = auto()

    # acknowledge that the previous message has been replicated
    REPLICATION_ACK = auto()
