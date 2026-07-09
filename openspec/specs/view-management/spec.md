# View Management

## Purpose

Define monitor View CRUD behavior. A View combines one video device and one
audio device, manages stream lifecycle through Server control logic, and
returns playable stream URLs for the frontend.

## Requirements

### Requirement: Create monitor views

The system SHALL expose `POST /api/v1/views` with a JSON request body modeled
by `ViewCreateRequest`. The request body SHALL contain `audio_id` and
`video_id`. These fields SHALL NOT be query parameters. When creating a View,
Server SHALL check the audio and video reference counts, send `UPDATE_STREAM`
start commands for devices whose previous reference count is zero, create the
View record, and start the merge pipeline.

#### Scenario: Swagger documents view creation input

- **WHEN** a frontend developer opens `POST /api/v1/views` in Swagger
- **THEN** `audio_id` and `video_id` are shown as JSON request body fields

#### Scenario: Create View and start new streams

- **WHEN** the client posts `{"audio_id": 1, "video_id": 1}` to
  `/api/v1/views` and neither stream is used by another View
- **THEN** Server sends `UPDATE_STREAM enable=true` for both devices
- **AND** Server creates the View record
- **AND** Server starts the merge process
- **AND** Server returns View details with playback URLs

#### Scenario: Create View with already-used streams

- **WHEN** the client creates a View using a device already referenced by
  another View
- **THEN** Server does not send a duplicate start command for that device
- **AND** Server returns a warning in the response

#### Scenario: Create View with missing devices

- **WHEN** `audio_id` or `video_id` does not exist
- **THEN** Server returns 404

### Requirement: Delete monitor views

The system SHALL expose `DELETE /api/v1/views/{view_id}`. Server SHALL delete
the View record transactionally, terminate the View merge process after the
database operation succeeds, then stop raw device streams whose reference count
reaches zero by sending `UPDATE_STREAM enable=false`.

#### Scenario: Delete last View reference

- **WHEN** a View is deleted and its audio and video devices have no remaining
  View references
- **THEN** Server deletes the View record
- **AND** Server terminates the merge process
- **AND** Server sends `UPDATE_STREAM enable=false` for both devices

#### Scenario: Delete View while streams are still referenced

- **WHEN** a View is deleted but its audio or video device is still referenced
  by another View
- **THEN** Server deletes the View record
- **AND** Server does not send `UPDATE_STREAM enable=false` for devices with
  remaining references

#### Scenario: Merge process already exited

- **WHEN** a View is deleted after its merge process has already exited
- **THEN** Server still deletes the database record and logs the process state

### Requirement: List monitor views

The system SHALL expose `GET /api/v1/views` and return all Views with fields
needed by the frontend, including View identifiers, device ids, creation time,
and playback URLs.

#### Scenario: List all Views

- **WHEN** the frontend requests `GET /api/v1/views`
- **THEN** Server returns all current Views

### Requirement: Get monitor View details

The system SHALL expose `GET /api/v1/views/{view_id}` and return the selected
View details, including related device information and playback URLs.

#### Scenario: Get one View

- **WHEN** the frontend requests `GET /api/v1/views/{view_id}`
- **THEN** Server returns that View if it exists
- **AND** Server returns 404 if it does not exist

### Requirement: View lifecycle changes are transactionally durable

The View service SHALL explicitly commit successful create/delete lifecycle
changes and SHALL roll back the active database session when an exception
prevents completion.

#### Scenario: Created View is visible after request completion

- **WHEN** `POST /api/v1/views` returns success
- **THEN** a subsequent `GET /api/v1/views` SHALL include the created View
- **AND** the referenced devices SHALL keep their updated `streaming` state

#### Scenario: Delete View commits release state

- **WHEN** `DELETE /api/v1/views/{view_id}` returns success
- **THEN** a subsequent `GET /api/v1/views/{view_id}` SHALL return 404
- **AND** devices whose reference count reached zero SHALL keep `streaming=false`

#### Scenario: Lifecycle operation fails

- **WHEN** View creation or deletion raises before returning a response
- **THEN** Server SHALL roll back the database session before propagating the error
