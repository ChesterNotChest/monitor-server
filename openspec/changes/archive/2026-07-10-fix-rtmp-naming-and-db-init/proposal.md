## Why

Two blockers prevent the system from working end-to-end outside test environments:

1. **RTMP stream naming misalignment**: Server internally uses three different formats to construct pull URLs (`video_{id}`, `audio_{id}`, `{name}_{type}_{id}`). Node pushes in `{device_name}_{device_type}_{device_id}` format. Only `build_pull_url` matches Node; FrameReader and YamnetRunner use their own formats and cannot pull the streams Node pushes.

2. **Database tables never created in production**: `app.py` startup calls `seed_admin()` which queries `users` table, but `Base.metadata.create_all()` is only invoked in test conftest. In production the tables don't exist, the seeder fails with a database error, and the `except Exception: pass` swallows it — no admin user is ever created.

## What Changes

- **Server**: Replace hardcoded URL formats in `vision_frame_reader.py` and `audio_yamnet.py` with calls to `build_pull_url()`, unifying on `{device_name}_{device_type}_{device_id}`
- **Server**: Call `Base.metadata.create_all(bind=engine)` in `app.py` startup before `seed_admin()`
- **Spec**: Create `node-server-stream-naming` spec enforcing `rtmp://{host}:{port}/live/{device_name}_{device_type}_{device_id}` as the single authoritative format for all node→server raw stream pull URLs
- **No Node changes required**: Node already uses the correct format

## Capabilities

### New Capabilities
- `node-server-stream-naming`: Mandatory RTMP naming convention — all raw device streams between Node and Server SHALL use `{device_name}_{device_type}_{device_id}`. Server SHALL enforce this by exclusively using `build_pull_url()` for constructing pull URLs.

### Modified Capabilities
<!-- None — existing API surface unchanged. -->

## Impact

- **Code changed**: `src/service/vision_module/vision_frame_reader.py` (use build_pull_url), `src/service/audio_module/audio_yamnet.py` (use build_pull_url + config), `src/app.py` (add create_all before seeder)
- **Spec created**: `openspec/specs/node-server-stream-naming/spec.md`
- **No breaking changes**: FrameReader and YamnetRunner already receive device IDs; the change only affects URL construction, not the interface
