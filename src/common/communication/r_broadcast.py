import logging
import time

from common.communication.sendreceive import SendReceive
from common.message import Message
from common.types import Address


class RBroadcast:
    """
    Provides reliable broadcast.
    Represents the group communication middleware layer of group communication (see fig. 3.1)
    """

    def __init__(self, deliver_callback, own_address: Address):
        self._deliver_callback = deliver_callback
        self.address = own_address

        self.sender = SendReceive(self.r_deliver, self.address)

        self._msgs_received_from_sender: dict[Address, list[tuple[int, int]]] = {}

        self._message_counter = 0

        # see documentation
        self._unique_identifier = int(time.time())

    def run(self):
        self.sender.run()

    def _generate_message_id(self) -> tuple[int, int]:
        message_id = (self._unique_identifier, self._message_counter)

        self._message_counter += 1

        return message_id

    def r_broadcast(self, to: set[Address], message: Message):

        for addr in to:
            assert isinstance(addr, tuple)

        rb_meta = dict(
            sender=self.address,
            message_id=self._generate_message_id(),
            to=list(to)
        )

        message.add_meta("r_broadcast", rb_meta)

        if self.broadcast(to, message) == 0:
            raise RuntimeError("Broadcast failed: No messages were delivered")

    def broadcast(self, to: set[Address], message: Message) -> int:
        """
        Broadcast a message to a group
        :param to:
        :param message:
        :return: number of successfully sent messages
        """
        delivered = 0
        for recipient in to:
            try:
                self.sender.send(recipient, message)
                delivered += 1
            except ConnectionRefusedError:
                logging.warning(f"Broadcast partially failed: Connection refused by {recipient}")
        return delivered

    def r_deliver(self, message: Message):
        rb_meta = message.meta["r_broadcast"]
        sender = tuple(rb_meta["sender"])
        message_id = rb_meta["message_id"]
        to = set([tuple(addr) for addr in rb_meta["to"]])

        # if the received message was sent by this object, there is nothing to do
        if self.address == sender:
            return

        # if the message was already received, there is also nothing to do
        if sender in self._msgs_received_from_sender.keys() and message_id in self._msgs_received_from_sender[sender]:
            return

        # if the message is unknown, mark it as received, forward it to others and deliver it:

        # mark as received
        if sender not in self._msgs_received_from_sender.keys(): self._msgs_received_from_sender[sender] = []
        self._msgs_received_from_sender[sender].append(message_id)

        others = to.copy().remove(self.address)
        if others:
            self.broadcast(others, message)

        # deliver
        self._deliver_callback(message)
