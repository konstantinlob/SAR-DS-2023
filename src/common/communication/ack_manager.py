import logging
from time import time

from common.communication.r_broadcast import RBroadcast
from common.message import Message, Topic, Command
from common.types import Address


class AckManager:
    """
    Reliably sends/broadcasts messages and (optionally) awaits acknowledgements.
    An error is thrown if the acknowledgement is not received on time.
    """

    def __init__(self, deliver_callback, own_address: Address):
        self.deliver_callback = deliver_callback
        self.address = own_address

        self.r_broadcaster = RBroadcast(self.deliver, self.address)

        # time in seconds after which a message must be acknowledged
        self.ack_timeout = 10

        self.message_id = 0
        # dict storing the IDs of requests awaiting acknowledgement and the time they expire
        self.awaiting_ack: dict[int, float] = dict()

    def run(self):
        """
        Run the socket handler loop and check for timeouts
        :return:
        """

        for message_id, timeout_at in self.awaiting_ack.items():
            if timeout_at < time():
                self.awaiting_ack.pop(message_id)
                raise RuntimeError("Ack timed out")

        self.r_broadcaster.run()

    def is_awaiting_ack(self) -> bool:
        return len(self.awaiting_ack) > 0

    def r_broadcast(self, to: set[Address], message: Message, expect_ack: bool = False):
        """
        :param expect_ack:
        :param to:
        :param message:
        :return:
        """
        if expect_ack:
            ack_meta = dict(
                message_id=self.message_id
            )
            message.add_meta("ack_manager", ack_meta)

            self.awaiting_ack[self.message_id] = time() + self.ack_timeout

            self.message_id += 1

        self.r_broadcaster.r_broadcast(to, message)

    def acknowledge_with_message(self, reply_message: Message, request_message: Message):
        """
        Send a response containing an acknowledgement to a message that requested it

        :param reply_message:
        :param request_message:
        :return:
        """

        ack_for: Address = request_message.get_origin()
        for_message_id = request_message.meta["ack_manager"]["message_id"]

        ack_meta = dict(
            for_message_id=for_message_id
        )
        reply_message.add_meta("ack_manager", ack_meta)

        self.r_broadcast({ack_for}, reply_message)

    def acknowledge(self, message: Message):
        """
        Send an acknowledgement to a message that requested it

        :param message:
        :return:
        """
        ack_msg = Message(
            topic=Topic.CLIENT,
            command=Command.ACK
        )

        self.acknowledge_with_message(ack_msg, message)

    def deliver(self, message: Message):
        """
        Forward the received message to the handler.
        If the received message is an acknowledgement for a previous request, mark the request as acknowledged.
        :param message:
        :return:
        """
        try:
            for_message_id = message.meta["ack_manager"]["for_message_id"]
        except KeyError:
            # The message is not an acknowledgement -> forward to handler
            logging.debug("Message does not contain acknowledgement, forwarding to handler")
            return self.deliver_callback(message)

        # only forward the message if it has not been acknowledged before and if it is an actual message
        if for_message_id in self.awaiting_ack.keys():
            self.awaiting_ack.pop(for_message_id)

            if message.command != Command.ACK:
                self.deliver_callback(message)
        else:
            logging.debug("Message is not in list of expected acknowledgements")
