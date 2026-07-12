# Auth Service

## Purpose

Define login, logout, current-user lookup, JWT signing/verification, and
password hashing behavior for Server authentication.

## Requirements

### Requirement: Auth runtime dependencies are declared

The system SHALL declare JWT and password hashing runtime dependencies in both
`requirements.txt` and `environment.yml`. JWT handling SHALL use
`python-jose[cryptography]`, and password hashing SHALL use `bcrypt`.

#### Scenario: Fresh CI image imports auth service

- **WHEN** Docker CI builds from `requirements.txt`
- **THEN** importing `src.service.auth_task` succeeds

#### Scenario: Conda development environment imports auth service

- **WHEN** developers update from `environment.yml`
- **THEN** importing `src.service.auth_task` succeeds

### Requirement: User login

The system SHALL expose `POST /api/v1/auth/login`. The endpoint SHALL accept
`username` and `password`, verify the password hash, and return a JWT access
token and user information when authentication succeeds.

#### Scenario: Login succeeds

- **WHEN** valid credentials are provided
- **THEN** Server returns `access_token`, `token_type`, and `user`

#### Scenario: Login fails

- **WHEN** the password is invalid or the user is inactive
- **THEN** Server returns 401

### Requirement: Current user lookup

The system SHALL expose `GET /api/v1/auth/me`. The endpoint SHALL parse the
Authorization bearer token, verify the JWT, and return the current user.

#### Scenario: Valid token

- **WHEN** the request includes a valid `Authorization: Bearer <token>` header
- **THEN** Server returns the current user's `id`, `username`, and `role`

#### Scenario: Missing or invalid token

- **WHEN** the token is missing or invalid
- **THEN** Server returns an authentication error
