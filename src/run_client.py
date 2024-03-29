from common.utils import enforce_requirements
enforce_requirements()

import argparse
import logging

from client import FileServiceClient as Client
from common.paths import parse_path

argument_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
argument_parser.add_argument('--server', type=str, help="Server address (host:port)",
                             default="localhost:50000")

argument_parser.add_argument('--user', type=str, help="Automatically authenticate using this user",
                             default="anonymous")
argument_parser.add_argument('--passwd', type=str, help="Automatically authenticate using this password",
                             default="anonymous")

argument_parser.add_argument('--watch', type=str, help="Watch folders", nargs='*', default=[])

args = vars(argument_parser.parse_args())


def main():
    server: str = args.get('server')
    user = args.get('user')
    passwd = args.get('passwd')

    host, port = server.split(":")
    port = int(port)

    client = Client()

    client.connect((host, port))
    client.auth(user, passwd)

    for watch_dir in args.get("watch"):
        client.add_watched_folder(parse_path(watch_dir))

    from time import sleep
    while True:
        client.run()
        sleep(.1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
