import os
import sys; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # noqa
import getpass
import socket
import typing as t
import watchdog
from watchdog.observers import Observer
from core.constants import SERVER_HOST, SERVER_PORT


def get_credentials() -> t.Tuple[str, str]:
    try:
        username = input("Username: ")
        password = getpass.getpass("Password: ")
    except KeyboardInterrupt:
        print("Ok Bye")
        sys.exit(1)
    return username, password


class Client:
    OPTIONS = [
        ("ADD", "Add directory to watchlist, and mirror its changes onto the server."),
        ("REMOVE", "Remove directory from watchlist (deletes backup on server aswell)."),
        ("LIST", "List currently watched directories."),
        ("EXIT", "Exit the App."),
    ]

    def __init__(self, username: str, password: str):
        self.username, self.password = username, password
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.watcher = watchdog.observers.Observer()
        self.watcher.start()  # todo: move to better place
        self.directories = []

    def add_to_watcher(self, path: str):
        self.watcher.add_handler_for_watch(self, path)
        self.directories.append(path)

    def remove_from_watcher(self, path: str):
        self.watcher.remove_handler_for_watch(self, path)
        self.directories.remove(path)

    def dispatch(self, event):
        print(f"Filesystem event: {event}")

    def run(self):
        self.connect()
        self.authenticate()
        return self.main() or 0

    def connect(self):
        self.connection.connect((SERVER_HOST, SERVER_PORT))

    def authenticate(self):
        message = f"AUTH:{self.username}:{self.password}"
        self.connection.sendall(message.encode())
        # TODO: Check response

    def main(self):
        while True:
            self.print_options()
            option = self.request_userinput()
            if option == "EXIT":
                break
            self.handle_option(option)

    def print_options(self):
        max_length = max(len(opt[1]) for opt in self.OPTIONS)
        print(f"+----+-{'-'*max_length}-+")
        for i, opt in enumerate(self.OPTIONS):
            print(f"| {str(i).rjust(2)} | {opt[1].ljust(max_length)} |")
        print(f"+----+-{'-'*max_length}-+")

    def request_userinput(self) -> str:
        all_options = {opt[0] for opt in self.OPTIONS}
        while True:
            inp = input("> ")
            try:
                return self.OPTIONS[int(inp)][0]
            except ValueError:
                inp = inp.upper()
                if inp in all_options:
                    return inp
                print("Bad Input")

    def handle_option(self, option: str):
        getattr(self, f'handle_option_{option.lower()}')()

    def handle_option_add(self):
        directory = input("Directory: ")
        self.add_to_watcher(directory)

    def handle_option_remove(self):
        directory = input("Directory: ")
        self.remove_from_watcher(directory)

    def handle_option_list(self):
        if not self.directories:
            print("Watching no directories")
            return
        print("Watching following directories:")
        print('-'*50)
        for directory in self.directories:
            print("-", directory)
        print('-'*50)


def main():
    username, password = get_credentials()
    return Client(username, password).run()


if __name__ == '__main__':
    sys.exit(main())
