# Active replication

The following document describes a distributed file server system with _n_ servers and one client.

## Communication

1. A middleware in the client attaches a unique ID before sending a request and adds this ID to a queue of pending requests, 
   together with a timestamp after which the request will time out.
2. If the client receives `ACK`, the ID is removed from this list.
3. If no `ACK` is received within the timeout, an error is raised.

### Middlewares

- AckManager: expects acknowledgement within specified time
- RBroadcast: reliable broadcast
  - also used for 1:1 messages for simplicity

## Message structure

| Field      | Description                                                              |
|------------|--------------------------------------------------------------------------|
| `topic`    | General topic                                                            |
| `command`  | Action within a topic                                                    |
| `params`   | Data for the execution of the action                                     |
| `meta_...` | Additional information inserted by middleware (one field per middleware) |
| `...`      | ...                                                                      |

### Topic `FILE`:

Sent from the client to the server:

| Command    | Params | Description |
|------------|:-------|-------------|
| `CREATED`  |        |             |
| `DELETED`  |        |             |
| `MODIFIED` |        |             |
| `MOVED`    |        |             |
| `WATCHED`  |        |             |

### Topic `CLIENT`:

Sent from the client to the server:

| Command | Params                               | Description                                                 |
|---------|:-------------------------------------|-------------------------------------------------------------|
| `KNOCK` |                                      | Establish initial connection to one of the servers          |
| `AUTH`  | `username`: _str_, `password`: _str_ | Authenticate client and register with all the other servers |

Sent from the server to the client:

| Command       | Params                              | Description                                 |
|---------------|:------------------------------------|---------------------------------------------|
| `ACK`         |                                     | Acknowledge message                         |
| `SET_SERVERS` | `servers`: _dict[str, Address]_     | Set the list of all servers                 |
| `ADD_SERVER`  | `name`: _str_, `address`: _Address_ | Add a new server to the list of all servers |

### Topic `REPLICATION`:

| Command       | Params                                                                  | Description                                                       |
|---------------|:------------------------------------------------------------------------|-------------------------------------------------------------------|
| `JOIN`        |                                                                         | Contact one of the existing servers and register as a new replica |
| `INITIALIZE`  | `name`: _str_, `servers`: _dict[str, Address]_, clients: _set[Address]_ | Set/Update the list of all servers                                |
| `ADD_SERVER`  | `name`: _str_, `address`: _Address_                                     | Add a new server to the list of all servers                       |
| `SET_CLIENTS` | ???                                                                     | Inform a newly connected server about all active clients          |


## Procedures

### New client connects to file servers

#### Assumptions

- Client knows the Address of one active server

#### Description

1. Client sends `CLIENT.KNOCK` to known server
2. Server informs client about all other servers using `CLIENT.SET_SERVERS`
3. Client connects to all active servers by broadcasting `CLIENT.AUTH`

#### Notes

- If a new server joins the group between step 2 and 3, the client if not informed about the server

### New server joins the group

#### Assumptions

- New server knows the Address of one active server

#### Description

1. New server sends `REPLICATION.JOIN` to known server
2. Known server informs new server about all active servers and clients and assigns a name to the new server using `REPLICATION.INITIALIZE`
3. New server introduces itself to all active servers using `REPLICATION.ADD_SERVER`
4. New server introduces itself to all clients using `CLIENT.ADD_SERVER`
