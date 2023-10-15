import socket


def get_network_identifier(host: str):
    if host in {"127.0.0.1", "localhost"}:
        return "localhost"
    else:
        # `socket.gethostbyname(socket.gethostname())` doesn't work always
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.connect(("8.8.8.8", 80))
                return client.getsockname()[0]
        except (socket.error, socket.gaierror):
            return host
