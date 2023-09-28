import os
import sys; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # noqa
import getpass
import socket
import typing as t
from pathlib import Path
import watchdog
import watchdog.events
from watchdog.observers import Observer
from core.constants import SERVER_HOST, SERVER_PORT
from core.packer import pack, unpack


ROOT = Path(__file__).parent.parent.absolute()


def get_credentials() -> t.Tuple[str, str]:
    try:
        username = input("Username: ")
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
        print(f"Watchdog: {event!r}")

    def on_created(self, event: watchdog.events.FileCreatedEvent):
        self.send(
            command="CREATED",
            body=dict(
                src_path=self.get_relative(event.src_path),
                is_directory=event.is_directory,
            )
        )

    def on_deleted(self, event: watchdog.events.FileDeletedEvent):
        self.send(
            command="DELETED",
            body=dict(
                src_path=self.get_relative(event.src_path),
                is_directory=event.is_directory,
            )
        )

    def on_moved(self, event: watchdog.events.FileMovedEvent):
        self.send(
            command="MOVED",
            body=dict(
                src_path=self.get_relative(event.src_path),
                dest_path=self.get_relative(event.dest_path),
                is_directory=event.is_directory,
            )
        )

    def on_modified(self, event: watchdog.events.FileModifiedEvent):
        #stat = os.stat(event.src_path)
        #permissions = stat.st_mode & 0o777
        self.send(
            command="MODIFIED",
            body=dict(
                src_path=self.get_relative(event.src_path),
                is_directory=event.is_directory,
                # permissions=permissions,
                # atime=stat.st_atime,
                # mtime=stat.st_mtime,
                # ctime=stat.st_ctime,
                new_content=None if event.is_directory else Path(event.src_path).read_bytes(),
            )
        )


class Client(watchdog.events.FileSystemEventHandler):
    OPTIONS = [
        ("ADD", "Add directory to watchlist, and mirror its changes onto the server."),
        ("REMOVE", "Remove directory from watchlist (deletes backup on server aswell)."),
        ("LIST", "List currently watched directories."),
        ("EXIT", "Exit the App."),
    ]

    def __init__(self, username: str, password: str):
        self.username, self.password = username, password

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rfile = self.connection.makefile('rb', -1)
        self.wfile = self.connection.makefile('wb', 0)

        self.watcher = watchdog.observers.Observer()
        self.watcher.start()  # todo: move to better place
        self.directories = {}

    def __del__(self):
        self.rfile.close()
        self.wfile.close()
        self.watcher.stop()

    def add_to_watcher(self, path: str):
        print(f"Add directory to watcher: {path!r}")
        watch = self.watcher.schedule(FileSystemEventHandler(self.send, path), path, recursive=False)
        self.directories[path] = watch
        self.send(
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
        return self.main() or 0

    def connect(self):
        self.connection.connect((SERVER_HOST, SERVER_PORT))

    def send(self, command: str, body):
        self.wfile.write(pack(dict(
            command=command,
            body=body,
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
            )
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
