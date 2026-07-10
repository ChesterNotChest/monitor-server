## Why

During the `fix-api-test-auth` change, systematic comparison of API specs against actual router implementations revealed 5 categories of misalignment. The specs describe routes, filters, and bind/unbind patterns that either don't exist in code or exist but were never wired up. These gaps block the team from using specs as an authoritative reference for Part B and Part C implementation.

## What Changes

- Register `event.py` router in `api/__init__.py` — full event query + stats API exists in code but not wired
- Remove ResponseAction API routes from `alert-group-crud-api` spec — model exists but CRUD/bind routes never implemented
- Remove GET-by-ID endpoints from all enum/alert-group/exception specs — routers only have GET (list) not GET by ID
- Fix enum route prefixes in `enum-crud-api` spec — actual routes use `/detection/entity-types` not `/entity-types`
- Remove bind/unbind (entities/actions/sounds) from `exception-crud-api` spec — routes don't exist
- Remove severity filter claim from `exception-api` spec — no filter param in router
- Remove ResponseAction references from `alert-group-api` spec — feature not in API layer
- Remove duplicate-409 from `enum-crud-api` — handler doesn't catch IntegrityError

## Capabilities

### New Capabilities
<!-- None — this aligns specs to existing code, no new capability is introduced. -->

### Modified Capabilities
- **event-query-api**: Event routes registered (code existed, was unwired)
- **alert-group-crud-api**: ResponseAction CRUD + bind/unbind removed (not implemented)
- **alert-group-api**: ResponseAction references + GET-by-ID removed
- **exception-crud-api**: Bind/unbind routes + GET-by-ID + severity filter removed
- **exception-api**: Severity filter claim removed
- **enum-crud-api**: Route prefixes corrected to `/detection/`; GET-by-ID + duplicate-409 removed

## Impact

- **Code changed**: `src/network/api/__init__.py` (register event router + stats router)
- **Specs changed**: `alert-group-crud-api`, `alert-group-api`, `exception-crud-api`, `exception-api`, `enum-crud-api`
- **No breaking changes**: All changes are spec-docs aligning to existing code behavior; router registration only adds routes
