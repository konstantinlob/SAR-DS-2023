import argparse
import logging
from pathlib import Path

from client import FileServiceClient as Client

argument_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
argument_parser.add_argument('--server', type=str, help="Server address (host:port)", required=True)

argument_parser.add_argument('--user', type=str, help="Automatically authenticate using this user")
argument_parser.add_argument('--passwd', type=str, help="Automatically authenticate using this password")

argument_parser.add_argument('--watch', type=str, help="Watch folders", nargs='*')

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
        client.add_watched_folder(Path(watch_dir))

    from time import sleep
    while True:
        client.run()
        sleep(.1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
