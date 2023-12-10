from enum import Enum

Command = Enum("Command", [
    "CREATED",
    "DELETED",
    "MOVED",
    "MODIFIED",
    "WATCHED",
    "AUTH"
])
