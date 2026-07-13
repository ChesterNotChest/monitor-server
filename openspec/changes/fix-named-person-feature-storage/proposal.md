## Why

Uploading a real named-person avatar extracts a 128D face encoding and stores it as a JSON array string in `named_persons.feat_json_id`. In production MySQL this JSON string is longer than the current `String(256)` column, so `POST /api/v1/persons/{id}/avatar/` fails with:

```text
Data too long for column 'feat_json_id'
```

This blocks the named-person / stranger recognition workflow from saving usable face features.

## What Changes

- Change `NamedPerson.feat_json_id` from `String(256)` to `Text`.
- Update the Named Person model spec to describe `feat_json_id` as full feature JSON storage.
- Add regression coverage for long face feature JSON values.
- Document the required production MySQL schema upgrade for existing databases.

## Capabilities

### Modified Capabilities

- `named-person-model`: `feat_json_id` stores the full serialized face feature JSON, not a short external reference.
- `named-person-crud`: avatar upload may persist a real 128D feature JSON string without failing due to column length.

## Impact

- **`src/models/named_person.py`**: `feat_json_id` column type changes to SQLAlchemy `Text`.
- **Existing MySQL deployments**: must run an idempotent `ALTER TABLE` to widen `named_persons.feat_json_id`.
- **Tests**: repository coverage includes long feature JSON storage.
