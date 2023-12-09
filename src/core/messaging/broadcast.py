from core.messaging.sendreceive import SendReceiveMiddleware
from core.utils.address import Address


class BroadcastMiddleware:
    """
    Provides broadcasting
    """

    def __init__(self, deliver_callback):
        self.sender = SendReceiveMiddleware(self.deliver)
        self.deliver_callback = deliver_callback

    def broadcast(self, to: set[Address], command, body, meta=None):
        for recipient in to:
            self.sender.send(recipient, command, body, meta)

    def deliver(self, message):
        self.deliver_callback(message)
