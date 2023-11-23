from flask import Flask, request

from server import PrimaryServer, BackupServer
from utils import Address

import argparse

parser = argparse.ArgumentParser(description='Run an instance of the file server')
parser.add_argument("--host")
parser.add_argument("--port")
parser.add_argument("--backup-for")


def run_server(is_primary: bool = True, host: str = "127.0.0.1", port: int = 5000, primary_at: Address = None):
    app = Flask(__name__)

    if is_primary:
        server = PrimaryServer(Address(host, port))

        @app.post("/replication/init-backup")
        def replication_init_backup():
            return server.handle_replication_init_backup(request)
    else:
        server = BackupServer(Address(host, port), primary_server=primary_at)

    @app.post("/client/init")
    def init_client():
        return server.handle_client_init(request)

    @app.post("/client/authenticate")
    def authenticate_client():
        return server.handle_client_authenticate(request)

    @app.post("/client/demo-message")
    def demo_message():
        return server.handle_client_demo_message(request)

    @app.post("/replication/set-backups")
    def replication_set_backup():
        return server.handle_replication_set_backup(request)

    server.run()

    app.run(host=host, port=port, debug=False)



if __name__ == "__main__":
    args = vars(parser.parse_args())

    if "backup_for" in args:
        is_primary = False
        primary_at = Address.parse(args["backup_for"])
    else:
        is_primary = True
        primary_at = None

    host = args["host"]
    port = int(args["port"])

    run_server(is_primary=is_primary, host=host, port=port, primary_at=primary_at)
