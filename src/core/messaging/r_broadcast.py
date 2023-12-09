from core.messaging.broadcast import BroadcastMiddleware
from core.utils.address import Address


class RBroadcastMiddleware:
    """
    Provides reliable broadcast.
    Represents the group communication middleware layer of group communication (see fig. 3.1)
    """

    def __init__(self, deliver_callback, own_address: Address):
        self.deliver_callback = deliver_callback
        self.address = own_address
        self.broadcaster = BroadcastMiddleware(self.r_deliver)

        self.msgs_received_from_sender: dict[Address, list[int]] = {}
        self.message_id = 0

    def r_broadcast(self, to: set[Address], command: str, body):
        meta = dict(
            sender=self.address,
            message_id=self.message_id,
            to=to
        )

        self.message_id += 1

        self.broadcaster.broadcast(to, command, body, meta)

    def r_deliver(self, message):
        sender = message["meta"]["sender"]
        message_id = message["meta"]["message_id"]

        if self.address == sender:
            return

        if message_id in self.msgs_received_from_sender[sender]:
            return

        self.msgs_received_from_sender[sender].append(message_id)

        self.deliver_callback(message)
