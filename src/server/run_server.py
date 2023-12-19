import argparse
import logging

from server import FileServiceServer as Server, FileServiceBackupServer as BackupServer

# TODO actually pass to server
parser = argparse.ArgumentParser(description='Run an instance of the file server')
parser.add_argument("--host")
parser.add_argument("--port")
parser.add_argument("--leader-host")
parser.add_argument("--leader-port")

if __name__ == '__main__':
    args = vars(parser.parse_args())
    logging.basicConfig(level=logging.INFO)

    host = args["host"]
    port = int(args["port"])
    own_addr = (host, port)

    if args.get("leader_host"):
        # add new server to group
        lead_host = args["leader_host"]
        lead_port = int(args["leader_port"])
        leader = (lead_host, lead_port)

        logging.info(f"Starting backup server at {own_addr}")
        server = BackupServer(own_addr)

        server.connect(leader)
    else:
        # start first server and create group
        logging.info(f"Starting new server at {own_addr}")
        server = Server(own_addr)

    from time import sleep

    while True:
        server.run()
        sleep(.1)
