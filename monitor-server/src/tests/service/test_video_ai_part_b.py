"""Part B video AI module tests."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
import time

import numpy as np
import pytest

from src.constants import FenceEventResult, SlowFastActionType, YOLOEntityType
from src.service.vision_module.vision_event_bus import ACTION, FACE, FENCE, event_bus
from src.service.vision_module.vision_annotation import draw_part_b_overlay
from src.service.vision_module.vision_face import FaceRecognizer, FaceResultStatus
from src.service.vision_module.vision_fence.fence_engine import FenceEngine, _FenceConfig
from src.service.vision_module.vision_slowfast.slowfast_runner import (
    ActionResult,
    SlowFastRunner,
    _select_ava_results,
    make_action_result,
    map_ava_label_to_action,
    map_kinetics_label_to_action,
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


def test_part_b_overlay_draws_track_labels_and_fence_polygon() -> None:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    tracks = [Track([20, 20, 80, 100], track_id=3, score=0.9)]

    annotated = draw_part_b_overlay(
        frame,
        tracks,
        face_labels={3: "Stranger"},
        action_labels={3: "pending"},
        fence_labels={3: "ENTERED"},
        fence_polygons=[[(10, 10), (100, 10), (100, 110), (10, 110)]],
    )

    assert annotated.shape == frame.shape
    assert np.any(annotated != frame)


class _FakeFaceLib:
    def __init__(self, encoding: np.ndarray) -> None:
        self.encoding = encoding

    def face_locations(self, _rgb_crop):
        return [(0, 10, 10, 0)]

    def face_encodings(self, _rgb_crop, _locations):
        assert _rgb_crop.flags["C_CONTIGUOUS"]
        return [self.encoding]

    def compare_faces(self, known_encodings, face_encoding, tolerance=0.6):
        return [np.linalg.norm(known - face_encoding) <= tolerance for known in known_encodings]


class _FallbackFaceLib(_FakeFaceLib):
    def face_encodings(self, _rgb_crop, _locations=None):
        assert _rgb_crop.flags["C_CONTIGUOUS"]
        if _locations is not None:
            raise TypeError("compute_face_descriptor(): incompatible function arguments")
        return [self.encoding]


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
            enable_spoof=False,
        )
        recognizer._face_lib = _FakeFaceLib(encoding)
        frame = np.zeros((120, 120, 3), dtype=np.uint8)
        tracks = [Track([10, 10, 100, 100], track_id=7, score=0.9)]

        # 2-step NAMED confirmation: need 2 recognition frames to confirm
        results = await recognizer.recognize_and_publish(frame, tracks, view_id=3)
        assert len(results) == 0  # first recognition frame → 1/2, not yet cached

        # skip 5 frames → hit second recognition frame
        for _ in range(5):
            recognizer.recognize(np.zeros((120, 120, 3), dtype=np.uint8), tracks)
        reused = recognizer.recognize(frame, tracks)

        assert reused[0].result == FaceResultStatus.NORMAL
        assert reused[0].person_name == "Alice"
        assert recognizer.get_face_labels() == {7: "Alice"}
    finally:
        await event_bus.unsubscribe(FACE, _collect)


def test_face_recognizer_retries_encoding_without_locations_on_dlib_compat_error() -> None:
    encoding = np.zeros(128)
    recognizer = FaceRecognizer(known_people=[(encoding, "Alice")], skip_frames=5, enable_spoof=False)
    recognizer._face_lib = _FallbackFaceLib(encoding)
    frame = np.zeros((120, 120, 3), dtype=np.uint8)
    tracks = [Track([10, 10, 100, 100], track_id=7, score=0.9)]

    # 2-step NAMED confirmation: need 2 recognition frames
    recognizer.recognize(frame, tracks)  # frame 1 → 1/2
    for _ in range(5):
        recognizer.recognize(np.zeros((120, 120, 3), dtype=np.uint8), tracks)
    results = recognizer.recognize(frame, tracks)  # frame 7 → 2/2 → cached

    assert results[0].result == FaceResultStatus.NORMAL
    assert results[0].person_name == "Alice"


@pytest.mark.asyncio
async def test_slowfast_runner_publishes_when_track_queue_is_full() -> None:
    received: list[dict] = []

    async def _collect(payload: dict) -> None:
        received.append(payload)

    def _infer(_clip):
        # _kinetics_infer mock: return single ActionResult (not list)
        return make_action_result(0, SlowFastActionType.FIGHTING, 0.88, source="test")

    await event_bus.subscribe(ACTION, _collect)
    try:
        runner = SlowFastRunner(clip_length=3, kinetics_infer=_infer)
        frame = np.zeros((16, 16, 3), dtype=np.uint8)

        # enqueue 2 frames → not ready
        assert runner.enqueue(5, frame) == []
        assert runner.enqueue(5, frame) == []
        # enqueue 3rd frame → clip ready, submit to thread pool, returns []
        assert runner.enqueue(5, frame) == []
        # thread pool inference should be done (mock _infer is instant)
        import time; time.sleep(0.05)
        results = runner.collect_results()

        assert len(results) == 1
        assert results[0].track_id == 5
    finally:
        await event_bus.unsubscribe(ACTION, _collect)


def test_slowfast_real_kinetics_is_disabled_by_default() -> None:
    runner = SlowFastRunner(clip_length=1)
    frame = np.zeros((32, 32, 3), dtype=np.uint8)

    assert runner.enqueue(1, frame) == []


def test_slowfast_kinetics_label_mapping_uses_local_action_enum() -> None:
    assert map_kinetics_label_to_action("walking the dog") == SlowFastActionType.WALKING
    assert map_kinetics_label_to_action("jogging") == SlowFastActionType.RUNNING
    assert map_kinetics_label_to_action("punching person") == SlowFastActionType.FIGHTING
    assert map_kinetics_label_to_action("making a cake") is None


def test_slowfast_ava_label_mapping_uses_local_action_enum() -> None:
    assert map_ava_label_to_action("smoke") == SlowFastActionType.SMOKING
    assert map_ava_label_to_action("fall down") == SlowFastActionType.FALLING
    assert map_ava_label_to_action("fight/hit (a person)") == SlowFastActionType.FIGHTING
    assert map_ava_label_to_action("talk to (e.g., self, a person, a group)") is None


def test_slowfast_kinetics_preprocess_creates_slow_and_fast_pathways() -> None:
    runner = SlowFastRunner(clip_length=32, enable_real_kinetics=True)
    clip = [np.zeros((80, 120, 3), dtype=np.uint8) for _ in range(32)]

    slow_pathway, fast_pathway = runner._preprocess_kinetics_clip(clip)

    assert tuple(fast_pathway.shape) == (1, 3, 32, 224, 224)
    assert tuple(slow_pathway.shape) == (1, 3, 8, 224, 224)


def test_slowfast_kinetics_labels_keep_multi_word_classes(tmp_path) -> None:
    labels_path = tmp_path / "kinetics_classnames.txt"
    labels_path.write_text("0 abseiling\nair drumming\nanswering questions\n", encoding="utf-8")

    runner = SlowFastRunner(kinetics_labels_path=labels_path)

    assert runner._kinetics_labels == ["abseiling", "air drumming", "answering questions"]


def test_slowfast_ava_labels_use_original_action_ids(tmp_path) -> None:
    labels_path = tmp_path / "ava.pbtxt"
    labels_path.write_text(
        'item { name: "fall down" id: 5 }\n'
        'item { name: "smoke" id: 54 }\n',
        encoding="utf-8",
    )

    runner = SlowFastRunner(ava_labels_path=labels_path)

    assert runner._ava_labels[4] == "fall down"
    assert runner._ava_labels[53] == "smoke"


def test_slowfast_ava_prepares_full_crop_box() -> None:
    runner = SlowFastRunner(enable_real_ava=True)

    box = runner._make_ava_full_crop_box()

    assert tuple(box.shape) == (1, 5)
    assert box.tolist()[0] == [0.0, 0.0, 0.0, 223.0, 223.0]


def test_slowfast_ava_mock_model_maps_smoking_result() -> None:
    import torch

    class _FakeAvaModel:
        def __call__(self, _inputs, _boxes):
            logits = torch.full((1, 80), -12.0)
            logits[0, 53] = 12.0
            return logits

    runner = SlowFastRunner(enable_real_ava=True, ava_confidence_threshold=0.5)
    runner._models_loaded = True
    runner._ava_model = _FakeAvaModel()
    runner._device = "cpu"
    clip = [np.zeros((80, 120, 3), dtype=np.uint8) for _ in range(32)]

    results = runner.infer_ava(7, clip)

    assert len(results) == 1
    assert results[0].track_id == 7
    assert results[0].action_type_id == int(SlowFastActionType.SMOKING)
    assert results[0].label == "SMOKING"
    assert results[0].source == "slowfast_ava:smoke"


def test_slowfast_ava_postprocess_suppresses_conflicting_actions() -> None:
    candidates = [
        ActionResult(1, int(SlowFastActionType.FALLING), "FALLING", 0.91, "ava"),
        ActionResult(1, int(SlowFastActionType.RUNNING), "RUNNING", 0.88, "ava"),
        ActionResult(1, int(SlowFastActionType.SITTING), "SITTING", 0.87, "ava"),
        ActionResult(1, int(SlowFastActionType.STANDING), "STANDING", 0.86, "ava"),
        ActionResult(1, int(SlowFastActionType.WALKING), "WALKING", 0.85, "ava"),
        ActionResult(1, int(SlowFastActionType.FIGHTING), "FIGHTING", 0.84, "ava"),
        ActionResult(1, int(SlowFastActionType.SMOKING), "SMOKING", 0.83, "ava"),
    ]

    selected = _select_ava_results(candidates, max_results=3)
    labels = [result.label for result in selected]

    assert labels == ["FALLING", "FIGHTING", "SMOKING"]
    assert "RUNNING" not in labels
    assert "SITTING" not in labels
    assert "STANDING" not in labels


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
    engine._fences_loaded_at = 999999.0  # 绕过 TTL DB 重载
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

    from src.service.vision_module.vision_face import face_recognizer as face_module

    pipeline = _Pipeline()
    processor = register_video_ai_hooks(pipeline, view_id=1)
    processor.face_recognizer._face_lib = None
    processor.face_recognizer._loaded_version = face_module._face_db_version
    processor.face_recognizer._last_load_time = time.monotonic()  # 绕过 TTL DB 重载
    processor.fence_engine._fences = []
    processor.fence_engine._fences_loaded_at = 999999.0  # 绕过 TTL DB 重载
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
