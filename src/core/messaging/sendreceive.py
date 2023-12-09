from core.packer import pack
from core.utils.address import Address


class SendReceiveMiddleware:
    """
    Represents the OS layer of group communication (see fig. 3.1)
    """

    def __init__(self, deliver_callback):
        self.deliver_callback = deliver_callback

    def send(self, to: Address, command: str, body, meta):
        """
        Send a message or file to the Client

        :param to:
        :param command:
        :param body: Additional parameters for the command
        :param meta: Metadata inserted by the middleware to provide reliable communication
        :return:
        """
        message = pack(dict(
            command=command,
            body=body,
            meta=meta
        ))

        url = f"http://{to.ip}:{to.port}/"

        # requests.post(url=url, data=message)
        # TODO
        raise NotImplementedError

    def receive(self):
        raise NotImplementedError
        # TODO
        # message = unpack(???
        # self.deliver_callback(message)
