# View Management (Delta)

## MODIFIED Requirements

### Requirement: Create monitor views

The system SHALL expose `POST /api/v1/views` with a JSON request body modeled
by `ViewCreateRequest`. The request body SHALL contain `audio_id` and
`video_id`. These fields SHALL NOT be query parameters. When creating a View,
Server SHALL check the audio and video reference counts, send `UPDATE_STREAM`
start commands for devices whose previous reference count is zero, create the
View record, and start the merge pipeline. The response SHALL be a flat
`ViewResponse` Pydantic model (not a nested dict with `"view"` key).

#### Scenario: Swagger documents view creation input

- **WHEN** a frontend developer opens `POST /api/v1/views` in Swagger
- **THEN** `audio_id` and `video_id` are shown as JSON request body fields

#### Scenario: Create View and start new streams

- **WHEN** the client posts `{"audio_id": 1, "video_id": 1}` to
  `/api/v1/views` and neither stream is used by another View
- **THEN** Server sends `UPDATE_STREAM enable=true` for both devices
- **AND** Server creates the View record
- **AND** Server starts the merge process
- **AND** Server returns flat `ViewResponse` with id, audio_id, video_id, playback URLs, and warnings

#### Scenario: Create View with already-used streams

- **WHEN** the client creates a View using a device already referenced by
  another View
- **THEN** Server does not send a duplicate start command for that device
- **AND** Server returns a warning in `ViewResponse.warnings`

#### Scenario: Create View with missing devices

- **WHEN** `audio_id` or `video_id` does not exist
- **THEN** Server returns 404

### Requirement: Service layer returns Pydantic model

`view_task.create_view()` SHALL return a `ViewResponse` Pydantic model instance (not a dict). Tests and callers SHALL use attribute access (`.id`, `.warnings`) to read fields.

#### Scenario: Service returns typed model

- **WHEN** `view_task.create_view(db, audio_id=..., video_id=...)` succeeds
- **THEN** the return value SHALL be a `ViewResponse` instance
- **AND** `result.warnings` SHALL be a `list[str]` accessible via attribute
