import logging
from sys import stdout

import messages.client
from utils import Address

logging.basicConfig(stream=stdout, level=logging.INFO)


class Client:
    port: int
    server: Address

    def __init__(self):
        self.server = Address("127.0.0.1", 5000)
        self.port = 6000

    def init(self):
        """
        Initialize connection to the server
        :return:
        """

        logging.info("Initializing client")
        r = messages.client.send_init(self.server, port=self.port)

    def authenticate(self, username, password):
        logging.info("Authenticating client")
        r = messages.client.send_authenticate(self.server, username, password, port=self.port)

    def send_demo_message(self, message: str):
        logging.info(f'Sending demo message: "{message}"')
        r = messages.client.send_demo_message(self.server, message, port=self.port)

    def set_server(self, new_server: Address):
        """
        This is called when the current primary server fails and a new server should be used
        :param new_server:
        :return:
        """
        logging.warning(f"New remote server {new_server}")
        self.server = new_server


from time import sleep

if __name__ == "__main__":
    client = Client()
    client.init()
    client.authenticate("user", "pass")

    i = 1
    while True:
        client.send_demo_message(f"Hello, this is demo message #{i}!")
        i += 1
        sleep(2)
