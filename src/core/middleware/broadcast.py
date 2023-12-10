from core.address import Address
from core.middleware.sendreceive import SendReceiveMiddleware


class BroadcastMiddleware:
    """
    Provides broadcasting
    """

    def __init__(self, deliver_callback, addr: Address):
        self.sender = SendReceiveMiddleware(self.deliver, addr)
        self.deliver_callback = deliver_callback

    def broadcast(self, to: set[Address], command, body, meta=None):
        for recipient in to:
            self.sender.send(recipient, command, body, meta)

    def deliver(self, message):
        self.deliver_callback(message)
