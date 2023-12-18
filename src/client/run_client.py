import argparse
import logging

from client import FileServiceClient as Client

argument_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
argument_parser.add_argument('--host', type=str, help="Host of the server")
argument_parser.add_argument('--port', type=int, help="Port of the server")

argument_parser.add_argument('--user', type=str, help="Automatically authenticate using this user")
argument_parser.add_argument('--passwd', type=str, help="Automatically authenticate using this password")

argument_parser.add_argument('--watch', type=str, help="Watch folders", nargs='*')

args = vars(argument_parser.parse_args())


def main():
    host = args.get('host')
    port = args.get('port')
    user = args.get('user')
    passwd = args.get('passwd')

    client = Client()

    client.connect((host, port))
    client.auth(user, passwd)

    client.add_watched_folder("client_files")  # TODO remove hardcoded path

    from time import sleep
    while True:
        client.run()
        sleep(.1)

    # for watch_dir in args.get("watch"):
    #    client.add_to_watcher(watch_dir)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
