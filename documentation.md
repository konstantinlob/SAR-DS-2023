# Active replication

The following document describes a distributed file server system with _n_ servers and one client.

## Communication

1. A middleware in the client attaches a unique ID before sending a request and adds this ID to a queue of pending
   requests,
   together with a timestamp after which the request will time out.
2. If the client receives `ACK`, the ID is removed from this list.
3. If no `ACK` is received within the timeout, an error is raised.

### Middlewares

- AckManager: expects acknowledgement within specified time
- RBroadcast: reliable broadcast
    - also used for 1:1 messages for simplicity
- SendReceive: handle 1:1 message transmission

#### RBroadcast

Reliable broadcast requires the ability to distinguish every sent message from each other.

A simple counter embedded into each `RBroadcast` object is an obvious solution, the recipient can then check if the
counter in combination with the client address was seen before or not.

However, this can lead to issues in the case where a sender is restarted: It will tag its first message with message ID
1 again, which means that the message will be ignored by all nodes who have previously received a message from this
address.

Therefore, it is necessary to embed another identifier within the message that uniquely identifies the actual
`RBroadcast` object. One possible source for this ID is the Unix timestamp at which the object was created.

## Message structure

| Field     | Description                                                                             |
|-----------|-----------------------------------------------------------------------------------------|
| `topic`   | General topic                                                                           |
| `command` | Action within a topic                                                                   |
| `params`  | Data for the execution of the action                                                    |
| `meta`    | Additional information inserted by middleware (dict containing one dict per middleware) |

### Topic `FILE`:

Sent from the client to the server:

| Command    | Params                                                           | Description                | Auth ? |
|------------|:-----------------------------------------------------------------|----------------------------|--------|
| `WATCHED`  | `path`: _str_                 `                                  | Synchronize another folder | yes    |
| `CREATED`  | `is_directory`´: _bool_, `src_path`: _str_                       |                            | yes    |
| `DELETED`  | `is_directory`´: _bool_, `src_path`: _str_                       |                            | yes    |
| `MODIFIED` | `is_directory`´: _bool_, `src_path`: _str_, `new_content`: _???_ |                            | yes    |
| `MOVED`    | `src_path`: _str_, `dest_path`: _str_                            |                            | yes    |
| `EXAMPLE`  | `example`: _str_                                                 | For demonstration purposes | anon   |

### Topic `CLIENT`:

Sent from the client to the server:

| Command | Params                               | Description                                                 |
|---------|:-------------------------------------|-------------------------------------------------------------|
| `KNOCK` |                                      | Establish initial connection to one of the servers          |
| `AUTH`  | `username`: _str_, `password`: _str_ | Authenticate client and register with all the other servers |

Sent from the server to the client:

| Command        | Params                     | Description                                 |
|----------------|:---------------------------|---------------------------------------------|
| `AUTH_SUCCESS` | `success`: _bool_          | Confirm that the client is authenticated    |
| `ERROR`        | `message`: _str_           |                                             |
| `SET_SERVERS`  | `servers`: _list[Address]_ | Set the list of all servers                 |
| `ADD_SERVER`   | `address`: _Address_       | Add a new server to the list of all servers |

### Topic `REPLICATION`:

| Command      | Params                                               | Description                                                       |
|--------------|:-----------------------------------------------------|-------------------------------------------------------------------|
| `CONNECT`    |                                                      | Contact one of the existing servers and register as a new replica |
| `INITIALIZE` | `servers`: _list[Address]_, clients: _list[Address]_ | Set/Update the list of all servers                                |
| `ADD_SERVER` | `server`: _Address_                                  | Add a new server to the list of all servers                       |

## Procedures

### New client connects to file servers

#### Assumptions

- Client knows the Address of one active server

#### Description

1. Client sends `CLIENT.KNOCK` to known server
2. Server informs client about all other servers using `CLIENT.SET_SERVERS`
3. Client connects to all active servers by broadcasting `CLIENT.AUTH`
4. Servers confirm login with `CLIENT.AUTH_SUCCESS`

#### Notes

- If a new server joins the group between step 2 and 3, the client if not informed about the server

### New server joins the group

#### Assumptions

- New server knows the Address of one active server

#### Description

1. New server sends `REPLICATION.CONNECT` to known server
2. Known server informs new server about all active servers and clients using `REPLICATION.INITIALIZE`
3. New server introduces itself to all active servers using `REPLICATION.ADD_SERVER`
4. New server introduces itself to all clients using `CLIENT.ADD_SERVER`
