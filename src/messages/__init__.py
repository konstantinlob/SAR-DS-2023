import requests

from utils import Address


def build_url(server: Address, endpoint: str):
    return f"http://{server.ip}:{server.port}/{endpoint}"


def post(server: Address, endpoint: str, params=None, data=None, client: Address = None, port: int = None):
    """
    Make a POST request to the server.
    Automatically sets required arguments.
    :param endpoint: API endpoint
    :param params: URL parameters
    :param data: POST data
    :param client: if the message is being forwarded, this is the original client
    :param port: if the message is being sent by the client, this is the client's port
    :return:
    """
    if params is None:
        params = {}

    if data is None:
        data = {}

    if port:
        params["port"] = port
    if client:
        params["client"] = client

    r = requests.post(
        build_url(server, endpoint),
        params=params,
        data=data
    )

    if r.status_code != 200:
        raise Exception
    return r
