## 1. Fix FrameReader RTMP URL

- [ ] 1.1 Replace `_build_rtmp_url(device_id)` with call to `build_pull_url(video_name, "video", video_id)`
- [ ] 1.2 Change `open()` signature from `(self, video_id: int)` to `(self, video_id: int, video_name: str)`
- [ ] 1.3 Update caller in `vision_pipeline.py` to pass `video_name` from VideoDevice lookup

## 2. Fix YamnetRunner RTMP URL

- [ ] 2.1 Replace hardcoded `rtmp://127.0.0.1:1935/live/audio_{id}` with `build_pull_url(audio_name, "audio", audio_id)`
- [ ] 2.2 Add `audio_name` parameter to `YamnetRunner.__init__()`
- [ ] 2.3 Move `import numpy` from function body to top of file

## 3. Fix DB init before seeder

- [ ] 3.1 Add `Base.metadata.create_all(bind=engine)` to `app.py` startup before `seed_admin()`
- [ ] 3.2 Replace bare `except Exception: pass` with `logger.warning("seed_admin failed: %s", e)`

## 4. Spec enforcement

- [ ] 4.1 Create `node-server-stream-naming` spec (ADDED capability)

## 5. Verify

- [ ] 5.1 Run `pytest src/tests/service/test_stream_pipeline.py -v` — pipeline tests pass
- [ ] 5.2 Run `pytest src/tests/service/test_yamnet_audio.py -v` — YAMNet tests pass (skip if weights missing)
- [ ] 5.3 Run `pytest src/tests/api/ -v` — API tests pass
- [ ] 5.4 Verify `app.py` startup creates tables and seeds admin without silent failure
