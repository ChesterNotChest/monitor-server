## Context

The regression test fix (`fix-api-test-auth`) required detailed comparison of 6 API test files against their corresponding router implementations. This surfaced broader misalignment: specs describe endpoints and behaviors that don't exist in code, and in one case (event API), code exists but is not registered.

The project has 48 specs under `openspec/specs/` covering models, APIs, and infrastructure. Several API-layer specs were written as design documents before implementation, and the implementations diverged or were never completed.

## Goals / Non-Goals

**Goals:**
- Every spec SHALL accurately describe the current API surface (routes, parameters, responses)
- Specs that describe unimplemented features SHALL have those features removed (can be re-added when implemented)
- The event query API SHALL be registered and functional (code exists, just unwired)

**Non-Goals:**
- Implementing new features (ResponseAction CRUD, exception bind/unbind, GET-by-ID endpoints)
- Changing the existing router implementations (except registering event routes)
- Modifying model-layer or repo-layer specs (ResponseAction model correctly exists)

## Decisions

### Decision 1: Remove from spec, don't add to code

For features described in specs but missing from code (ResponseAction CRUD routes, exception bind/unbind, GET-by-ID), we remove from specs rather than implement.

**Rationale**: These features are part of Part C (`tasks-c-audio-alert.md`). Implementing them now would be scope creep. Removing from spec makes the current state truthful. The Part C implementer can restore these requirements from git history when ready.

**Alternative considered**: Leave spec as-is with "TODO" markers. Rejected — an inaccurate spec is worse than a missing spec; it misleads implementers about what exists.

### Decision 2: Register event router (code fix)

The `event.py` module has complete routes for event listing, detail, and statistics. It was simply never imported in `__init__.py`. We fix this by adding the import and router registration.

**Rationale**: This is a one-line bug fix, not a feature implementation. The code, service layer, and tests all exist. The router is accidentally unwired.

### Decision 3: Keep ResponseAction model spec

The `response-enum-model` spec correctly describes the `ResponseAction` model and `alert_group_responses` association table that exist in the database. We keep this spec. Only the API-layer spec (`alert-group-crud-api`) is trimmed.

### Decision 4: Use spec-driven delta format

Each affected spec gets a delta file under `specs/<spec-name>/spec.md` in the change directory. The delta uses `## REMOVED Requirements` sections to remove inaccurate requirements, and `## MODIFIED Requirements` where only specific scenarios change.

## Risks / Trade-offs

- **Risk**: Part C implementer doesn't know to restore removed requirements → **Mitigation**: Git history preserves old specs; the Part C task list already references these features
- **Trade-off**: Registering event routes exposes them without RBAC protection → the event routes currently have no `require_permission` decorator. This is acceptable: event data is read-only query, and RBAC can be added in a follow-up
