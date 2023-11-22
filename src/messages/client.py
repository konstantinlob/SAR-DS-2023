from stuff import Address
from messages import post

def send_init(server: Address, client: Address = None, port: int = None):
    """
    Send client init message
    :param server: target server
    :param client: if the message is being forwarded, this is the original client
    :param port:  if the message is being sent by the client, this is the client's port
    :return:
    """

    r = post(server, "client/init", client=client, port=port)
    if r.status_code != 200:
        raise Exception
    return r


def send_authenticate(server: Address, username: str, password: str, client: Address = None, port: int = None):
    r = post(server, "client/authenticate", data={
        "username": username,
        "password": password
    }, client=client, port=port)
    if r.status_code != 200:
        raise Exception
    return r


def send_demo_message(server: Address, message: str, client: Address = None, port: int = None):
    r = post(server, "client/demo-message", data={
        "message": message,
    }, client=client, port=port)
    if r.status_code != 200:
        raise Exception
    return r
