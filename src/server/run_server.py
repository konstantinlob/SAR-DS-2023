import logging

from core.address import Address
from server import PrimaryServer, BackupServer

import argparse

parser = argparse.ArgumentParser(description='Run an instance of the file server')
parser.add_argument("--host")
parser.add_argument("--port")
parser.add_argument("--backup-for")

if __name__ == '__main__':
    args = vars(parser.parse_args())
    logging.basicConfig(level=logging.INFO)

    if args["backup_for"]:
        is_primary = False
        backup_for = Address.parse(args["backup_for"])
    else:
        is_primary = True
        backup_for = None

    host = args["host"]
    port = int(args["port"])
    addr = Address(host, port)

    if is_primary:
        server = PrimaryServer(addr)
    else:
        server = BackupServer(addr, backup_for)

    while True:
        server.comm.sender.handle_sockets()
