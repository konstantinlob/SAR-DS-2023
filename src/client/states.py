from enum import Enum


class ClientState(Enum):
    # client has just started
    STARTED = 0,
    # client has requested the connection to the group
    CONNECTING = 1,
    # client has received server details and is attempting to authenticate
    AUTHENTICATING = 2,
    # authentication successful, running normally
    RUNNING = 3
