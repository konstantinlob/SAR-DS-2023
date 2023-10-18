# DGLS File Service (DS Assignment 1.4)

This utility synchronizes a set of folders between the client and the server, much like other cloud services like dropbox.

The client and server can run the same computer, or communicate over a (local) network.

## Usage Manual

### Client
#### Setup
1. Ensure Python 3 is installed.

2. install watchdog with ``pip install watchdog``

#### Usage
- In the `src/` folder, run the client script:

   ```bash
   python3 client.py [--server-host {HOST}] [--server-port {PORT}]
   ```

Authenticate with your username and password. Login without a password is also available with the `anonymous` username.

##### Options
- Add: Watch a directory for changes. Add directories to be tracked with their relative path.
- Remove: Stop watching a directory.
- List: View watched directories.
- Exit: Close the client.

### Server
#### Setup
- Install Python 3.
- In the `src/` folder, run the server script:

```bash
python3 server.py
```

