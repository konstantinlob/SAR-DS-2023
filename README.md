# DGLS File Service (DS Assignment 1.4)

This utility synchronizes a set of folders between the client and the server, much like other cloud services like
dropbox.

The client and server can run the same computer, or communicate over a (local) network.


## Installation

1. Ensure **Python 3.12** is installed. Use a virtual environment if your system Python version is not up-to-date.

2. install dependencies: ``pip install -r requirements.txt``


## Usage Manual

### Client

- Make sure a network of at least one server is up and running
- In the `src/` folder, run the client script:

   ```bash
   python3 run_client.py
   ```
  
- The following arguments can be used:

  ```
  usage: run_client.py [-h] [--server SERVER] [--user USER] [--passwd PASSWD] [--watch [WATCH ...]]

  options:
    -h, --help           show this help message and exit
    --server SERVER      Server address (host:port) (default: localhost:50000)
    --user USER          Automatically authenticate using this user (default: anonymous)
    --passwd PASSWD      Automatically authenticate using this password (default: anonymous)
    --watch [WATCH ...]  Watch folders (default: [])
  ```
- logging in as anonymous is possible for demonstration purposes, but you will not be able to change files on the server
- you can use `--watch` followed by multiple paths to watch multiple folders`


### Server

- In the `src/` folder, run the server script:

    ```bash
    python3 run_server.py
    ```
    
- The following arguments can be used:

  ```
  usage: run_server.py [-h] [--address ADDRESS] --storage-dir STORAGE_DIR [--join JOIN]
  
  Run an instance of the file server
  
  options:
    -h, --help            show this help message and exit
    --address ADDRESS     Own address (host:port)
    --storage-dir STORAGE_DIR
                          Path to folder that stores the uploaded files
    --join JOIN           Join an existing server group at the given address (host:port)
  ```

- When running multiple servers, it is necessary to specify different addresses for each of them
- Running the server without the `--join` option will start a new "primary" server
  / a new group consisting of only one server
- Other servers can later be started with the `--join` option, they will then join the group and provide redundancy in
  case one of the servers fails

