import argparse
import getpass
import typing as t
from sys import exit

from client import Client
from core.constants import SERVER_HOST, SERVER_PORT

argument_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
argument_parser.add_argument('--server-host', type=str, help="Host of the server")
argument_parser.add_argument('--server-port', type=int, help="Port of the server")

argument_parser.add_argument('--user', type=str, help="Automatically authenticate using this user")
argument_parser.add_argument('--passwd', type=str, help="Automatically authenticate using this password")

argument_parser.add_argument('--watch', type=str, help="Watch folders", nargs='*')

args = vars(argument_parser.parse_args())


def get_credentials() -> t.Tuple[str, str]:
    """
    Get credentials for connecting to the file server
    :return: username, password
    """

    # first, check if the credentials were passed as arguments
    args_user = args.get("user")
    args_password = args.get("passwd")

    # if the complete credentials were passed as arguments, we are done here.
    if args_user and args_password:
        print("Using credentials provided as arguments")
        return args_user, args_password

    try:
        # If the username was passed as an argument, use it. If not, ask the user now.
        username = args_user if args_user else input("Username: ")
        password = getpass.getpass("Password: ")
    except KeyboardInterrupt:
        print("Ok Bye")
        exit(1)
    return username, password


def main():
    host = args.get('server_host') if args.get('server_host') else SERVER_HOST
    port = args.get('server_port') if args.get('server_port') else SERVER_PORT

    username, password = get_credentials()

    client = Client(username, password)

    client.connect(host, port)
    client.authenticate()

    for watch_dir in args.get("watch"):
        client.add_to_watcher(watch_dir)

    client.main()

    return client


if __name__ == '__main__':
    exit(main())
