from enum import Enum


class ServerState(Enum):
    # server has just started
    STARTED = 0,
    # server has requested connection to the group
    CONNECTING = 1
    # server has received server and client details and is attempting to introduce itself to other nodes
    JOINING = 2,
    # server has joined server group and is registered with clients, running normally
    RUNNING = 3
