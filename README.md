# Usage Manual

## Client
### Setup
1. Ensure Python 3 is installed.

2. install watchdog with ``pip install watchdog``

### Usage
- Run the client script:
   ```bash
   python3 client.py [--server-host {HOST}] [--server-port {PORT}]
   ```
Authenticate with your username and password.

#### Options
- Add: Watch a directory for changes. Add directories to be tracked with their relative path.
- Remove: Stop watching a directory.
- List: View watched directories.
- Exit: Close the client.

## Server
### Setup
- Install Python 3.
- Run the server script:
```bash
python3 server.py
```

