class Address:
    ip: str
    port: int

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = int(port)
