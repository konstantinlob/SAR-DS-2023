import os
import sys
import threading
import time
from datetime import datetime
from queue import Queue

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # noqa
import socket
import getpass
import argparse
import typing as t
from pathlib import Path
import watchdog
import watchdog.events as evt
from watchdog.observers import Observer
from core.constants import SERVER_HOST, SERVER_PORT
from core.packer import pack, unpack


ROOT = Path(__file__).parent.parent.absolute()

argument_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
argument_parser.add_argument('--server-host', type=str, help="Host of the server")
argument_parser.add_argument('--server-port', type=int, help="Port of the server")

argument_parser.add_argument('--verbose', type=bool, default=False, action=argparse.BooleanOptionalAction, help="Print more messages")

argument_parser.add_argument('--user', type=str, help="Automatically authenticate using this user")
argument_parser.add_argument('--passwd', type=str, help="Automatically authenticate using this password")

argument_parser.add_argument('--watch', type=str, help="Watch folders", nargs='*')


args = vars(argument_parser.parse_args())
DEBUG = args.get("verbose", False)


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
        sys.exit(1)
    return username, password


class FileSystemEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, send, path):
        self.send = send
        self.path = Path(path)

    def get_relative(self, path: str) -> str:
        return os.path.join(
            self.path.name,
            os.path.relpath(path, self.path)
        )

    def on_any_event(self, event):
        if DEBUG:
            print(f"Watchdog: {datetime.now().isoformat()} : {event!r}")

    def on_created(self, event: t.Union[evt.DirCreatedEvent, evt.FileCreatedEvent]):
        self.send(
            command="CREATED",
            body=dict(
                src_path=self.get_relative(event.src_path),
                is_directory=event.is_directory,
            )
        )

    def on_deleted(self, event: t.Union[evt.DirDeletedEvent, evt.FileDeletedEvent]):
        self.send(
            command="DELETED",
            body=dict(
                src_path=self.get_relative(event.src_path),
                is_directory=event.is_directory,
            )
        )

    def on_moved(self, event: t.Union[evt.DirMovedEvent, evt.FileMovedEvent]):
        self.send(
            command="MOVED",
            body=dict(
                src_path=self.get_relative(event.src_path),
                dest_path=self.get_relative(event.dest_path),
                is_directory=event.is_directory,
            )
        )

    def on_modified(self, event: t.Union[evt.DirModifiedEvent, evt.FileModifiedEvent]):
        fp = Path(event.src_path)
        self.send(
            command="MODIFIED",
            body=dict(
                src_path=self.get_relative(event.src_path),
                is_directory=event.is_directory,
                new_content=None if event.is_directory or not fp.is_file() else fp.read_bytes(),
            )
        )


class Client(watchdog.events.FileSystemEventHandler):
    OPTIONS = [
        ("ADD", "Add directory to watchlist, and mirror its changes onto the server."),
        ("REMOVE", "Remove directory from watchlist."),
        ("LIST", "List currently watched directories."),
        ("EXIT", "Exit the App."),
    ]

    def __init__(self, username: str, password: str):
        self.username, self.password = username, password

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rfile = self.connection.makefile('rb', -1)
        self.wfile = self.connection.makefile('wb', 0)
        self.message_queue = Queue()
        self.message_counter = 0
        self.ignored_ids=[]

        self.watcher = watchdog.observers.Observer()
        self.watcher.start()  # todo: move to better place
        self.directories = {}

    def __del__(self):
        self.rfile.close()
        self.wfile.close()
        self.watcher.stop()

    def add_message_to_queue(self, command: str, body):
        self.message_queue.put((command, body))

    def wait_for_acknowledgment(self):
        while self.waiting_for_ack:
            self.process_server_responses()
            time.sleep(0.1)

    def process_server_responses(self):
        # Check for server responses and handle the ACK message
        command, body = self.get_response()
        if command == "ACK": #and body['id'] == self.message_counter:
            print(f"Received ACK") #from correct ID: {self.message_counter}")
            self.waiting_for_ack = False
            #self.ignored_ids += self.message_counter
        else:
            print(f"Received unexpected response: {command}, {body}")


    def process_message_queue(self):
        while self.message_queue.not_empty:
            command, body = self.message_queue.get()
            self.waiting_for_ack = True
            self.send(command, body, id=self.message_counter)
            print(f"sent {command}")
            self.wait_for_acknowledgment()
            time.sleep(0.1)


    def add_to_watcher(self, path: str):
        if path in self.directories:
            raise KeyError("Directory is already watched")
        print(f"Add directory to watcher: {path!r}")
        watch = self.watcher.schedule(FileSystemEventHandler(self.send, path), path, recursive=True)
        self.directories[path] = watch
        self.add_message_to_queue(
            command="WATCHED",
            body=dict(
                src_path=path,
            )
        )

    def remove_from_watcher(self, path: str):
        print(f"Remove directory from watcher: {path!r}")
        watch = self.directories[path]
        self.watcher.unschedule(watch)
        del self.directories[path]

    def run(self):
        self.connect()
        self.authenticate()
        threading.Thread(target=self.process_message_queue).start()

        if args.get("watch"):
            for watch_dir in args.get("watch"):
                self.add_to_watcher(watch_dir)

        return self.main() or 0

    def connect(self):
        host = args.get('server_host') if args.get('server_host') else SERVER_HOST
        port = args.get('server_port') if args.get('server_port') else SERVER_PORT
        self.connection.connect((host, port))

    def send(self, command: str, body, id: int):
        self.message_counter+=1
        self.wfile.write(pack(dict(
            command=command,
            body=body,
            id=id
        )))

    def get_response(self) -> t.Tuple[str, dict]:
        message = unpack(self.rfile)
        print(f"Got: {message!r}")
        command = message['command']
        body = message['body']
        return command, body

    def authenticate(self):
        self.send(
            command="AUTH",
            body=dict(
                username=self.username,
                password=self.password,
            ),
            id=0
        )
        command, body = self.get_response()
        if command != "AUTH":
            raise KeyError("Bad Response Command")
        if not body['success']:
            raise RuntimeError("Login not successful")

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
        try:
            getattr(self, f'handle_option_{option.lower()}')()
        except Exception as error:
            print(f"Program says {type(error).__name__} with {error!r}")

    def handle_option_add(self):
        directory = input("Directory: ")
        path = ROOT / directory
        if not path.is_dir():
            raise NotADirectoryError(f"{directory!r} not found")
        self.add_to_watcher(directory)

    def handle_option_remove(self):
        directory = input("Directory: ")
        path = ROOT / directory
        if path not in self.directories:
            raise KeyError(f"{directory!r} not found in watched directories")
        self.remove_from_watcher(directory)

    def handle_option_list(self):
        if not self.directories:
            print("Watching no directories")
            return
        print("Watching following directories:")
        print('-'*50)
        for directory in self.directories.keys():
            print("-", directory)
        print('-'*50)


def main():
    username, password = get_credentials()
    return Client(username, password).run()


if __name__ == '__main__':
    sys.exit(main())
