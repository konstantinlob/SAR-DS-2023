import logging

from server import Server

import argparse

# TODO actually pass to server
parser = argparse.ArgumentParser(description='Run an instance of the file server')
parser.add_argument("--host")
parser.add_argument("--port")

if __name__ == '__main__':
    args = vars(parser.parse_args())
    logging.basicConfig(level=logging.INFO)

    host = args["host"]
    port = args["port"]

    server = Server()

    from time import sleep
    while True:
        server.run()
        sleep(.1)
