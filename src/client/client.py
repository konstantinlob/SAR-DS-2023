import os
import sys
import typing as t
from pathlib import Path

import watchdog
from watchdog.observers import Observer
from core.utils.address import Address

from filesystem import ClientFileSystemEventHandler

from core.messaging.sendreceive import SendReceiveMiddleware

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

ROOT = Path(__file__).parent.parent.absolute()


class Client:
    OPTIONS = [
        ("ADD", "Add directory to watchlist, and mirror its changes onto the server."),
        ("REMOVE", "Remove directory from watchlist."),
        ("LIST", "List currently watched directories."),
        ("EXIT", "Exit the App."),
    ]

    def __init__(self, username: str, password: str):
        self.username, self.password = username, password

        self.comm = SendReceiveMiddleware(self.deliver, Address("localhost", 50100)) #TODO do NOT hardcode the address
        self.__primary_server = None

        self.watcher = watchdog.observers.Observer()
        self.watcher.start()  # todo: move to better place
        self.directories = {}

    def __del__(self):
        self.watcher.stop()

    @property
    def server(self):
        if self.__primary_server:
            return self.__primary_server
        raise Exception

    def add_to_watcher(self, path: str):
        if path in self.directories:
            raise KeyError("Directory is already watched")
        print(f"Add directory to watcher: {path!r}")
        watch = self.watcher.schedule(ClientFileSystemEventHandler(self.send, path), path, recursive=True)
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

    def connect(self, host, port):
        self.__primary_server = Address(host, port)

    def send(self, command: str, body):
        self.comm.send(
            self.server,
            command,
            body
        )

    def deliver(self, message):
        raise NotImplementedError

    def authenticate(self):
        self.send(
            command="AUTH",
            body=dict(
                username=self.username,
                password=self.password,
            )
        )

    def main(self):
        while True:
            self.print_options()
            option = self.request_userinput()
            if option == "EXIT":
                break
            self.handle_option(option)

    def print_options(self):
        max_length = max(len(opt[1]) for opt in self.OPTIONS)
        print(f"+----+-{'-' * max_length}-+")
        for i, opt in enumerate(self.OPTIONS):
            print(f"| {str(i).rjust(2)} | {opt[1].ljust(max_length)} |")
        print(f"+----+-{'-' * max_length}-+")

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
        print('-' * 50)
        for directory in self.directories.keys():
            print("-", directory)
        print('-' * 50)
