class Address:
    ip: str
    port: int

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port

    @classmethod
    def parse(cls, string):
        """
        Parse String to Address object
        :param string: string
        :return: Address object
        """
        ip, port = string.split(":")
        return cls(ip, int(port))

    def __hash__(self):
        return hash((self.ip, self.port))

    def __eq__(self, other):
        if not isinstance(other, Address):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.ip == other.ip and self.port == other.port

    def __str__(self):
        return f"{self.ip}:{self.port}"
