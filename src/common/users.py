from enum import Enum

known_users = {
    "sar": "sar",
    "sza": "sza",
    "samuel": "konstantin"
}


class AccessType(Enum):
    UNAUTHENTICATED = 0
    ANONYMOUS = 1
    AUTHORIZED = 2


def check_auth(username, password) -> AccessType:
    if username == "anonymous":
        return AccessType.ANONYMOUS
    elif username in known_users.keys() and password == known_users[username]:
        return AccessType.AUTHORIZED
    else:
        return AccessType.UNAUTHENTICATED
