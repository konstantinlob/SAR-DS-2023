from sys import version_info
# needed for typing support
required_version = (3, 12)
if version_info < required_version:
    raise ImportError(f"Your Python version {version_info} is not supported. "
                      f"Please use Python {required_version[0]}.{required_version[1]} or higher.")

import argparse
import logging
from common.paths import parse_path
from pathlib import Path

from server import FileServiceServer as Server, FileServiceBackupServer as BackupServer

parser = argparse.ArgumentParser(description='Run an instance of the file server')
parser.add_argument("--address", help="Own address (host:port)", default="localhost:50000")
parser.add_argument("--storage-dir", help="Path to folder that stores the uploaded files", required=True)
parser.add_argument("--join", help="Join an existing server group at the given address(host:port)")

if __name__ == '__main__':
    args = vars(parser.parse_args())
    logging.basicConfig(level=logging.INFO)

    storage_dir = parse_path(args.get("storage_dir"))
    host, port = args.get('address').split(':')
    port = int(port)

    own_addr = (host, port)

    if args.get("join"):
        # add new server to group
        lead_host, lead_port = args.get('join').split(':')
        lead_port = int(lead_port)
        leader = (lead_host, lead_port)

        logging.info(f"Starting backup server at {own_addr}")
        server = BackupServer(own_addr, storage_dir)

        server.connect(leader)
    else:
        # start first server and create group
        logging.info(f"Starting new server at {own_addr}")
        server = Server(own_addr, storage_dir)

    from time import sleep

    while True:
        server.run()
        sleep(.1)
