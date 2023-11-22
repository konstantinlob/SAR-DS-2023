import requests

from stuff import Address


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

    # confirm that either the original client or the port is set, but not both
    if client is None and port is None:
        raise ValueError
    if client is not None and port is not None:
        raise ValueError

    if port:
        params["port"] = port
    if client:
        params["client"] = client

    return requests.post(
        build_url(server, endpoint),
        params=params,
        data=data
    )


