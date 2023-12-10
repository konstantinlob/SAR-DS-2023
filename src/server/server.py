import logging
import os
import sys
from pathlib import Path

from core.address import Address
from core.commands import Command
from core.middleware.sendreceive import SendReceiveMiddleware

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # noqa

WATCHED_DIRECTORIES_PATH = "watched"
FILES_ROOT = Path(WATCHED_DIRECTORIES_PATH).absolute()
FILES_ROOT.mkdir(parents=True, exist_ok=True)
SPACE_MARGIN = 50 * 1 << 20  # 50 MiB
USERS = {
    "anonymous": "",
    "sar": "sar",
    "sza": "sza",
    "konstantin": ""
}


# TCP/UDP range ports open: 50000 - 50200


def real_path(path: str) -> Path:
    real = (FILES_ROOT / path).absolute()
    if os.path.commonpath([str(FILES_ROOT), real]) != str(FILES_ROOT):
        raise PermissionError("Bad path")
    return real


class FileServer:
    def __init__(self, addr: Address):
        self.comm = SendReceiveMiddleware(self.deliver_from_client, addr)

    def deliver_from_client(self, message):
        command = message["command"]
        body = message["body"]
        client_ip, client_port = message["meta"]["client"]
        client = Address(client_ip, client_port)

        print(f"Received command: {command!r}")
        print(f"Received body: {body!r}")

        match command:
            case Command.CREATED:
                self.handle_client_file_created(**body)
            case Command.DELETED:
                self.handle_client_file_deleted(**body)
            case Command.MOVED:
                self.handle_client_file_moved(**body)
            case Command.MODIFIED:
                self.handle_client_file_modified(**body)
            case Command.WATCHED:
                self.handle_client_file_watched(**body)
            case Command.AUTH:
                self.handle_client_auth(client, **body)
            case _:
                raise ValueError

    def handle_client_file_watched(self, src_path: str):
        src_path = real_path(src_path)
        src_path.mkdir(parents=True, exist_ok=True)

    def handle_client_file_created(self, src_path: str, is_directory: bool):
        src_path = real_path(src_path)
        if is_directory:
            src_path.mkdir()
        else:
            src_path.touch()

    def handle_client_file_modified(self, src_path: str, is_directory: bool,
                                    new_content: bytes):  # permissions, atime, mtime, ctime,
        src_path = real_path(src_path)
        if new_content is not None:
            with open(src_path, 'wb') as file:
                file.write(new_content)
        # src_path.chmod(permissions)
        # os.utime(src_path, (atime, mtime))

    def handle_client_file_moved(self, src_path: str, dest_path: str, is_directory: bool):
        src_path = real_path(src_path)
        dist_path = real_path(dest_path)
        src_path.rename(dist_path)

    def handle_client_file_deleted(self, src_path: str, is_directory: bool):
        src_path = real_path(src_path)
        if is_directory:
            src_path.rmdir()
        else:
            src_path.unlink()

    def handle_client_auth(self, client: Address, username: str, password: str):
        logging.debug(f"Login attempt as {username}/{password}")

        success = username in USERS.keys() and USERS[username] == password

        logging.debug(f"Login successful: {username}/{password}")

        self.comm.send(
            client,
            Command.AUTH,
            dict(success=success)
        )
