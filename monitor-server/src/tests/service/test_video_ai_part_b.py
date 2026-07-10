"""Part B video AI module tests."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pytest

from src.constants import FenceEventResult, SlowFastActionType, YOLOEntityType
from src.service.vision_module.vision_event_bus import ACTION, FACE, FENCE, event_bus
from src.service.vision_module.vision_face import FaceRecognizer, FaceResultStatus
from src.service.vision_module.vision_fence.fence_engine import FenceEngine, _FenceConfig
from src.service.vision_module.vision_slowfast.slowfast_runner import (
    SlowFastRunner,
    make_action_result,
)
from src.service.vision_module.vision_tracking import ByteTracker, ByteTrackerState
from src.service.vision_module.vision_types import Track
from src.service.vision_module.video_ai_processor import register_video_ai_hooks


@dataclass
class _Detection:
    bbox: list[float]
    class_id: int = 0
    confidence: float = 0.9
    entity_type_id: int = YOLOEntityType.PERSON


def test_byte_tracker_keeps_stable_track_id_for_overlapping_person() -> None:
    tracker = ByteTracker(track_thresh=0.5, match_thresh=0.5)

    first = tracker.update([_Detection([10, 10, 100, 100])])
    second = tracker.update([_Detection([12, 10, 102, 100])])

    assert tracker.state == ByteTrackerState.ACTIVE
    assert len(first) == 1
    assert len(second) == 1
    assert second[0].track_id == first[0].track_id


def test_byte_tracker_ignores_non_person_detection() -> None:
    tracker = ByteTracker(track_thresh=0.5, match_thresh=0.5)

    tracks = tracker.update([
        _Detection([10, 10, 100, 100], class_id=2, entity_type_id=YOLOEntityType.CAR),
    ])

    assert tracks == []
    assert tracker.state == ByteTrackerState.IDLE


class _FakeFaceLib:
    def __init__(self, encoding: np.ndarray) -> None:
        self.encoding = encoding

    def face_locations(self, _rgb_crop):
        return [(0, 10, 10, 0)]

    def face_encodings(self, _rgb_crop, _locations):
        return [self.encoding]

    def compare_faces(self, known_encodings, face_encoding, tolerance=0.6):
        return [np.linalg.norm(known - face_encoding) <= tolerance for known in known_encodings]


@pytest.mark.asyncio
async def test_face_recognizer_matches_known_person_and_publishes() -> None:
    received: list[dict] = []

    async def _collect(payload: dict) -> None:
        received.append(payload)

    await event_bus.subscribe(FACE, _collect)
    try:
        encoding = np.zeros(128)
        recognizer = FaceRecognizer(
            known_people=[(encoding, "Alice")],
            skip_frames=5,
        )
        recognizer._face_lib = _FakeFaceLib(encoding)
        frame = np.zeros((120, 120, 3), dtype=np.uint8)
        tracks = [Track([10, 10, 100, 100], track_id=7, score=0.9)]

        results = await recognizer.recognize_and_publish(frame, tracks, view_id=3)
        reused = recognizer.recognize(frame, tracks)

        assert results[0].result == FaceResultStatus.NORMAL
        assert results[0].person_name == "Alice"
        assert reused[0].person_name == "Alice"
        assert recognizer.get_face_labels() == {7: "Alice"}
        assert received[-1]["labels"] == {7: "Alice"}
    finally:
        await event_bus.unsubscribe(FACE, _collect)


@pytest.mark.asyncio
async def test_slowfast_runner_publishes_when_track_queue_is_full() -> None:
    received: list[dict] = []

    async def _collect(payload: dict) -> None:
        received.append(payload)

    def _infer(_clip):
        return make_action_result(0, SlowFastActionType.FIGHTING, 0.88, source="test")

    await event_bus.subscribe(ACTION, _collect)
    try:
        runner = SlowFastRunner(clip_length=3, kinetics_infer=_infer)
        frame = np.zeros((16, 16, 3), dtype=np.uint8)

        assert await runner.enqueue_and_publish(5, frame, view_id=9) == []
        assert await runner.enqueue_and_publish(5, frame, view_id=9) == []
        results = await runner.enqueue_and_publish(5, frame, view_id=9)

        assert len(results) == 1
        assert results[0].track_id == 5
        assert received[-1]["actions"][0]["action_type_id"] == int(SlowFastActionType.FIGHTING)
    finally:
        await event_bus.unsubscribe(ACTION, _collect)


@pytest.mark.asyncio
async def test_fence_engine_enters_and_resets_after_leave_frames() -> None:
    received: list[dict] = []

    async def _collect(payload: dict) -> None:
        received.append(payload)

    fence = _FenceConfig(
        id=1,
        name="Gate",
        coords=[(0, 0), (100, 0), (100, 100), (0, 100)],
        dwell_time=10,
        density=0.5,
        leave_frames=2,
    )
    engine = FenceEngine(view_id=2, fences=[fence])
    inside = [Track([10, 10, 50, 50], track_id=4, score=0.9)]
    outside = [Track([200, 200, 250, 250], track_id=4, score=0.9)]

    await event_bus.subscribe(FENCE, _collect)
    try:
        entered = await engine.check_and_publish(inside, frame_timestamp=1.0)
        assert entered[0].result == FenceEventResult.ENTERED
        assert entered[0].entered is True

        assert await engine.check_and_publish(inside, frame_timestamp=2.0) == []

        assert await engine.check_and_publish(outside, frame_timestamp=3.0) == []
        reset = await engine.check_and_publish(outside, frame_timestamp=4.0)
        assert reset[0].entered is False
        assert received[-1]["fences"][0]["entered"] is False
    finally:
        await event_bus.unsubscribe(FENCE, _collect)


@pytest.mark.asyncio
async def test_video_ai_processor_registers_frame_hook_and_sets_tracks() -> None:
    class _Pipeline:
        def __init__(self) -> None:
            self.hooks = []

        def register_frame_hook(self, hook) -> None:
            self.hooks.append(hook)

    pipeline = _Pipeline()
    processor = register_video_ai_hooks(pipeline, view_id=1)
    processor.face_recognizer._face_lib = None
    processor.fence_engine._fences = []
    processor.slowfast_runner.clip_length = 99

    ctx = SimpleNamespace(
        frame=np.zeros((120, 120, 3), dtype=np.uint8),
        frame_id=1,
        timestamp=1.0,
        detections=[_Detection([10, 10, 100, 100])],
        tracks=None,
        view_id=1,
    )

    assert len(pipeline.hooks) == 1
    await pipeline.hooks[0](ctx)

    assert ctx.tracks is not None
    assert len(ctx.tracks) == 1
