import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # noqa
import socket
import traceback
import socketserver
from pathlib import Path
from core.constants import SERVER_HOST as HOST, SERVER_PORT as PORT
from core.packer import pack, unpack
from core.network import get_network_identifier

WATCHED_DIRECTORIES_PATH = "../watched"
FILES_ROOT = Path(WATCHED_DIRECTORIES_PATH).absolute()
FILES_ROOT.mkdir(parents=True, exist_ok=True)
SPACE_MARGIN = 50 * 1 << 20  # 50 MiB
USERS = ("anonymous", "sar", "sza", "konstantin")
PASSWORDS = ("", "sar", "sza", " ")

# TCP/UDP range ports open: 50000 - 50200


def real_path(path: str) -> Path:
    real = (FILES_ROOT / path).absolute()
    if os.path.commonpath([str(FILES_ROOT), real]) != str(FILES_ROOT):
        raise PermissionError("Bad path")
    return real


class ConnectionHandler(socketserver.StreamRequestHandler):

    def __init__(self):
        self.message_id=0
    def get_response(self):
        response = unpack(self.rfile)
        command = response['command']
        body = response['body']
        id = response['id']
        return command, body, id


    def send(self, command: str, body):
        """
        Send a message or file to the Client

        :param command:
        :param body:
        """
        self.wfile.write(pack(dict(
            command=command,
            body=body,
        )))


    def send_ack(self):
        self.send(command="ACK", body=dict())#id=self.message_id))
        print(f"sent ACK!")
        print("-"*25)


    def handle_error(self, error: Exception):
        print(f"Handle Error: {type(error).__name__}: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)
        self.send(
            command="ERROR",
            body=dict(
                error=type(error).__name__,
                detail=str(error),
            )
        )


    def handle(self) -> None:
        try:
            print(f"New Request from {self.client_address}")
            self.do_handshake()
            self.handle_requests()
        except (BrokenPipeError, ConnectionError):
            pass
        # removed: why would we want to catch all Exceptions?
        #except Exception as error:
        #    pass  # This will suppress other exceptions
        finally:
            self.request.close()  # Close the client connection


    def do_handshake(self):
        command, body, id = self.get_response()
        if command != "AUTH":
            raise ValueError("Authentication first required")
        username = body['username']
        password = body['password']
        print(f"Login attempt from {username!r}")
        try:
            user_index = USERS.index(username)
        except ValueError:
            raise ValueError("User not found")
        if password != PASSWORDS[user_index]:
            raise ValueError("Invalid Password")
        print(f"Login successfully of {username!r}")
        self.send(
            command="AUTH",
            body=dict(
                success=True,
            )
        )


    def handle_requests(self):
        while True:
            command, body, id = self.get_response()
            print(f"Received command: {command!r}")
            print(f"Received body: {body!r}")
            # print(f"Received id: {id!r}")
            handler = getattr(self, f'handle_{command.lower()}', None)
            if handler is None:
                raise LookupError("unknown command")
            else:
                handler(**body)
            #body['id']=self.message_id
            self.send_ack()


    def handle_watched(self, src_path: str):
        src_path = real_path(src_path)
        src_path.mkdir(parents=True, exist_ok=True)


    def handle_created(self, src_path: str, is_directory: bool):
        src_path = real_path(src_path)
        if is_directory:
            src_path.mkdir()
        else:
            src_path.touch()


    def handle_modified(self, src_path: str, is_directory: bool,
                        new_content: bytes):  # permissions, atime, mtime, ctime,
        src_path = real_path(src_path)
        if new_content is not None:
            with open(src_path, 'wb') as file:
                file.write(new_content)
        # src_path.chmod(permissions)
        # os.utime(src_path, (atime, mtime))


    def handle_moved(self, src_path: str, dest_path: str, is_directory: bool):
        src_path = real_path(src_path)
        dist_path = real_path(dest_path)
        src_path.rename(dist_path)


    def handle_deleted(self, src_path: str, is_directory: bool):
        src_path = real_path(src_path)
        if is_directory:
            src_path.rmdir()
        else:
            src_path.unlink()


if __name__ == '__main__':
    with socketserver.ForkingTCPServer((HOST, PORT), RequestHandlerClass=ConnectionHandler) as server:
        print("Server is up")
        print(f"Connect client to {get_network_identifier(HOST)}:{PORT} / {socket.getfqdn(HOST)}:{PORT}")
        server.serve_forever()
