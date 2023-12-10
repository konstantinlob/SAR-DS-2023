from core.address import Address
from core.commands import Command
from core.middleware.sendreceive import SendReceiveMiddleware


class RBroadcastMiddleware:
    """
    Provides reliable broadcast.
    Represents the group communication middleware layer of group communication (see fig. 3.1)
    """

    def __init__(self, deliver_callback, own_address: Address):
        self.deliver_callback = deliver_callback
        self.address = own_address

        self.sender = SendReceiveMiddleware(self.r_deliver, self.address)

        self.msgs_received_from_sender: dict[Address, list[int]] = {}
        self.message_id = 0

    def r_broadcast(self, to: set[Address], command: Command, body, msg_meta=None):
        broadcast_meta = dict(
            sender=(self.address.ip, self.address.port),
            message_id=self.message_id,
            to=[(a.ip, a.port) for a in to]
        )

        self.message_id += 1

        self.broadcast(to, command, body, msg_meta, broadcast_meta)

    def broadcast(self, to: set[Address], command: Command, body, msg_meta=None, broadcast_meta=None):
        for recipient in to:
            self.sender.send(recipient, command, body, msg_meta, broadcast_meta)


    def r_deliver(self, message):
        sender_ip, sender_port = message["broadcast_meta"]["sender"]
        sender = Address(sender_ip, sender_port)
        message_id = message["broadcast_meta"]["message_id"]

        # if the received message was sent by this object, there is nothing to do
        if self.address == sender:
            return

        # if the message was already received, there is also nothing to do
        if sender in self.msgs_received_from_sender.keys() and message_id in self.msgs_received_from_sender[sender]:
            return

        # if the message is unknown, mark it as received and deliver it
        if sender not in self.msgs_received_from_sender.keys(): self.msgs_received_from_sender[sender] = []
        self.msgs_received_from_sender[sender].append(message_id)

        self.deliver_callback(message)
