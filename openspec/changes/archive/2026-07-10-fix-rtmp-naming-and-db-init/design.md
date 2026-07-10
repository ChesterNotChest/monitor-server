## Context

Server internally uses three different RTMP pull URL formats, only one of which (`build_pull_url`) matches Node's push format. Additionally, `app.py` never creates database tables before calling `seed_admin()`, causing a silent failure in production.

## Goals / Non-Goals

**Goals:**
- Unify all Server-side RTMP pull URLs to `{device_name}_{device_type}_{device_id}` exclusively via `build_pull_url()`
- Ensure DB tables exist before `seed_admin()` runs in production
- Encode the naming convention as a mandatory spec

**Non-Goals:**
- Changing Node code (already compliant)
- Changing the push URL format for web-facing streams (`/view/{view_id}` — separate concern)

## Decisions

### Decision 1: FrameReader passes device_name and device_type to build_pull_url

`_build_rtmp_url(device_id)` currently hardcodes `video_{device_id}`. Replace with a call to `build_pull_url(video_name, "video", video_id)`.

FrameReader.open() signature changes from `(self, video_id: int)` to `(self, video_id: int, video_name: str)`. The device type is always `"video"` for FrameReader (it only handles video), so it's hardcoded in the call. The caller (AIPipeline / vision_task) already receives `video_id`; it must additionally pass `video_name` from the VideoDevice record.

### Decision 2: YamnetRunner uses build_pull_url with config

YamnetRunner currently hardcodes `127.0.0.1:1935/live/audio_{self._audio_id}`. Replace with `build_pull_url(audio_name, "audio", audio_id)`. The host and port are already resolved by `build_pull_url` via `settings.RTMP_HOST` / `settings.RTMP_PORT`. YamnetRunner must accept `audio_name` at construction time.

### Decision 3: DB init in startup — minimal addition

Add `Base.metadata.create_all(bind=engine)` immediately before `seed_admin()` in `app.py`'s `@app.on_event("startup")`. This is the same pattern used in test conftest. It's idempotent (no-op if tables already exist). Also replace the bare `except Exception: pass` with a logged warning so failures are visible.

### Decision 4: Single truth source — node-server-stream-naming spec

Create a new spec `node-server-stream-naming` that SHALL be referenced by both Node and Server teams. The spec mandates `rtmp://{host}:{port}/live/{device_name}_{device_type}_{device_id}` as the only valid format for raw device streams flowing Node→Server.

## Risks / Trade-offs

- **Risk**: Changing FrameReader.open() signature breaks AIPipeline → **Mitigation**: AIPipeline is the only caller; update it in the same change
- **Risk**: YamnetRunner constructor change is **BREAKING** for any code that instantiates it → **Mitigation**: YamnetRunner is not yet wired to any caller (Part C gap), so no callers to update
