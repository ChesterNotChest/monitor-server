# Node WSS Connection

## Purpose

Server maintains the WebSocket command channel used to authenticate Nodes,
track Node presence, and send stream control commands.

## Requirements

### Requirement: Server authenticates Node WSS connections

Server SHALL expose a WebSocket endpoint for Node connections. A connecting Node
SHALL send its token as the first message. When authentication succeeds, Server
SHALL register the WebSocket connection and mark the Node online.

#### Scenario: Node authenticates successfully

- **WHEN** a Node connects and sends a valid token
- **THEN** Server registers the connection in the connection registry
- **AND** Server marks the Node as connected with an updated `last_seen`

#### Scenario: Node token is invalid

- **WHEN** a Node connects with an invalid token
- **THEN** Server rejects the connection and does not register it

### Requirement: Server returns device mappings after authentication

After Node authentication succeeds, Server SHALL query the `VideoDevice` and
`AudioDevice` rows registered for that Node and return them in the auth response.
The response SHALL let Node build `server_device_id -> device_name` mappings.

`server_device_id` SHALL mean the Server database id for the corresponding
`VideoDevice` or `AudioDevice`. In Server command payloads this value is named
`device_id`.

#### Scenario: Existing devices are returned

- **WHEN** Node authentication succeeds and Server has `VideoDevice(id=1, name="Integrated Camera")`
- **THEN** Server returns `videos: [{id: 1, name: "Integrated Camera"}]`

#### Scenario: No registered devices

- **WHEN** Node authentication succeeds and no devices are registered for that Node
- **THEN** Server returns empty `videos` and `audios` lists

### Requirement: Server sends stream commands by Server device id

Server SHALL send `UPDATE_STREAM` commands with `device_type`, `device_id`, and
`enable`. `device_id` SHALL be the Server database id for the selected
`VideoDevice` or `AudioDevice`, not a local Node device id.

#### Scenario: Start a mapped video stream

- **WHEN** Server needs Node to publish `VideoDevice(id=1, name="Integrated Camera")`
- **THEN** Server sends `{"command":"UPDATE_STREAM","device_type":"video","device_id":1,"enable":true}`
- **AND** Node resolves `video 1 -> Integrated Camera` through its authenticated mapping

#### Scenario: Stop a mapped audio stream

- **WHEN** Server needs Node to stop `AudioDevice(id=2, name="Microphone Array")`
- **THEN** Server sends `{"command":"UPDATE_STREAM","device_type":"audio","device_id":2,"enable":false}`

### Requirement: Server tracks Node connection state

Server SHALL remove a Node connection from the registry when the WebSocket
disconnects and mark the Node offline.

#### Scenario: Node disconnects

- **WHEN** a registered Node WebSocket disconnects
- **THEN** Server removes the connection from the registry and marks the Node offline

### Requirement: Server receives heartbeat messages

Server SHALL accept heartbeat messages from authenticated Nodes without routing
them to stream lifecycle handlers.

#### Scenario: Heartbeat received

- **WHEN** Server receives `{"type":"heartbeat"}` from an authenticated Node
- **THEN** Server updates liveness state without changing stream state

## ADDED Requirements

### Requirement: WebSocket endpoint addresses are documented

The WebSocket endpoint SHALL be exposed at two paths:

- `ws://<host>:<port>/ws` — primary endpoint
- `ws://<host>:<port>/api/v1/ws` — API-prefixed alias

Both paths SHALL use the same handler. The Node SHALL connect with its token as a query parameter: `ws://<host>:<port>/ws?token=<node_token>`.

#### Scenario: Node connects with token query parameter

- **WHEN** a Node opens a WebSocket connection to `/ws?token=<token>`
- **THEN** Server extracts the token from the query string and authenticates the Node

### Requirement: Heartbeat interval is specified

The Node SHALL send heartbeat messages (`{"type":"heartbeat"}`) at a regular interval. Server SHALL expect heartbeats at a 30-second interval. Server SHALL mark a Node as disconnected if no heartbeat or other message is received within 90 seconds (3 missed intervals).

#### Scenario: Heartbeat timeout

- **WHEN** Server has not received any message from a Node for 90 seconds
- **THEN** Server marks the Node as disconnected and removes the WebSocket from the registry

### Requirement: Authentication error format

When authentication fails, Server SHALL close the WebSocket connection with a close code and a JSON error message. The error message SHALL include the reason for failure.

#### Scenario: Invalid token rejection

- **WHEN** a Node connects with an invalid or expired token
- **THEN** Server sends `{"error": "invalid_token", "detail": "Token is invalid or expired"}` and closes the connection with code 4001
