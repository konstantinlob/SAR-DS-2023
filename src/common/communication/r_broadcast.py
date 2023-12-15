from common.communication.sendreceive import SendReceive
from common.message import Message
from common.types import Address


class RBroadcast:
    """
    Provides reliable broadcast.
    Represents the group communication middleware layer of group communication (see fig. 3.1)
    """

    def __init__(self, deliver_callback, own_address: Address):
        self.deliver_callback = deliver_callback
        self.address = own_address

        self.sender = SendReceive(self.r_deliver, self.address)

        self.msgs_received_from_sender: dict[Address, list[int]] = {}
        self.message_id = 0

    def run(self):
        self.sender.run()

    def r_broadcast(self, to: set[Address], message: Message):

        for addr in to:
            assert isinstance(addr, tuple)

        rb_meta = dict(
            sender=self.address,
            message_id=self.message_id,
            to=list(to)
        )

        message.add_meta("r_broadcast", rb_meta)

        self.message_id += 1

        self.broadcast(to, message)

    def broadcast(self, to: set[Address], message: Message):
        for recipient in to:
            self.sender.send(recipient, message)

    def r_deliver(self, message: Message):
        rb_meta = message.meta["r_broadcast"]
        sender = tuple(rb_meta["sender"])
        message_id = rb_meta["message_id"]
        to = set([tuple(addr) for addr in rb_meta["to"]])

        # if the received message was sent by this object, there is nothing to do
        if self.address == sender:
            return

        # if the message was already received, there is also nothing to do
        if sender in self.msgs_received_from_sender.keys() and message_id in self.msgs_received_from_sender[sender]:
            return

        # if the message is unknown, mark it as received, forward it to others and deliver it:

        # mark as received
        if sender not in self.msgs_received_from_sender.keys(): self.msgs_received_from_sender[sender] = []
        self.msgs_received_from_sender[sender].append(message_id)

        # update the sender and forward to others
        message.meta["r_broadcast"]["sender"] = self.address
        others = to.copy().remove(self.address)
        if others:
            self.broadcast(others, message)

        # deliver
        self.deliver_callback(message)
