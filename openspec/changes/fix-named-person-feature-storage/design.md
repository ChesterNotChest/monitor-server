## Design

`extract_face_encoding()` returns a JSON array string containing 128 floating-point values. The serialized form is commonly several kilobytes, so bounded string columns are not appropriate.

Use SQLAlchemy `Text` for `NamedPerson.feat_json_id`:

- SQLite tests map it to an unbounded text affinity.
- MySQL maps it to `TEXT`, which is sufficient for a 128D JSON encoding.
- The API response remains unchanged: `feat_json_id` is still `str | None`.

## Migration

The project currently uses `Base.metadata.create_all()` and has no Alembic migration runner. `create_all()` creates new databases correctly after the model change but does not alter existing MySQL tables. Existing production databases need this one-time upgrade:

```sql
ALTER TABLE named_persons MODIFY feat_json_id TEXT NULL;
```

The deployment README records the Docker command form used on the production server.

## Risks

- Existing code may treat `feat_json_id` as a short identifier by name. The current runtime already stores the full JSON string there, so this change aligns the schema with implementation.
- MySQL `TEXT` is large enough for 128D face encodings. If future encodings become much larger, the column can be upgraded to `MEDIUMTEXT`.
