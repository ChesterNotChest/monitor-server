# Schema Convention

## Purpose

Define how `src/schema/` is organized for HTTP and WSS protocol models, and
keep FastAPI/OpenAPI behavior aligned with declared runtime dependencies.

## Requirements

### Requirement: Schema modules are split by protocol

`src/schema/` SHALL be split into `schema/http/` for REST request/response
models and `schema/wss/` for WebSocket command models. HTTP and WSS schemas
SHALL be maintained independently because their consumers and documentation
mechanisms differ.

#### Scenario: Schema directory layout

- **WHEN** developers inspect `src/schema/`
- **THEN** it contains separate `http/` and `wss/` packages
- **AND** each package contains its own `__init__.py`

### Requirement: HTTP schemas render in Swagger

Pydantic models under `schema/http/` SHALL be used as FastAPI router request
body parameters and `response_model` declarations. These models SHALL be
rendered automatically in Swagger UI at `/docs`, including field names, types,
and required/optional markers.

#### Scenario: REST schema is visible in Swagger

- **WHEN** a frontend developer opens `/docs`
- **THEN** REST request bodies and response schemas are visible without
  separate manual API documentation

#### Scenario: View creation request body

- **WHEN** `ViewCreateRequest` is used by the `POST /api/v1/views` router
- **THEN** Swagger shows `audio_id` and `video_id` as JSON request body fields

### Requirement: Multipart REST dependencies are declared

The system SHALL declare the `python-multipart` runtime dependency in both
`requirements.txt` and `environment.yml` whenever FastAPI routes use multipart
form handling, including `File` and `UploadFile` parameters. This keeps Docker
CI builds and Conda development environments aligned with OpenAPI route
registration.

#### Scenario: Avatar upload route is imported in CI

- **WHEN** a REST router defines an avatar or file upload endpoint with
  `UploadFile`
- **THEN** application import during pytest collection succeeds in a fresh
  Docker image built from `requirements.txt`

### Requirement: WSS schemas use Pydantic and manual protocol docs

Pydantic models under `schema/wss/` SHALL define WebSocket message formats
between Server and Node. These models SHALL be used for serialization and
deserialization validation in code, but SHALL NOT rely on OpenAPI for message
level documentation because WebSocket command payloads are outside the REST
OpenAPI surface.

#### Scenario: WSS protocol lookup

- **WHEN** developers need the Server-to-Node WSS message format
- **THEN** they inspect `src/schema/wss/node_commands.py` and the paired
  markdown/OpenSpec documentation

### Requirement: Cross-protocol models are not shared

HTTP and WSS schema packages SHALL not import each other's protocol models.
If a concept appears in both REST and WSS, each protocol SHALL define its own
model so the field sets can evolve independently.

#### Scenario: Device information appears in REST and WSS

- **WHEN** REST `GET /nodes/{id}/videos` and WSS `get_devices_response` both
  return device information
- **THEN** `schema/http/` and `schema/wss/` each define their own device model
