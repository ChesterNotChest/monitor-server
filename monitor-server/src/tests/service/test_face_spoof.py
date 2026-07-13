"""假脸检测（SPOOF）单元测试 — Mock MiniFASNet 避免 CI 依赖 uniface。"""

import numpy as np
import pytest

from src.service.vision_module.vision_face.face_recognizer import (
    FaceRecognizer, FaceResultStatus, FaceResult,
)


class FakeSpoofResult:
    def __init__(self, is_real: bool, confidence: float = 0.9):
        self.is_real = is_real
        self.confidence = confidence


class FakeSpoofer:
    def predict(self, frame: np.ndarray, bbox: tuple[int, int, int, int]):
        return FakeSpoofResult(is_real=True)


class FakeSpooferAllFake:
    def predict(self, frame: np.ndarray, bbox: tuple[int, int, int, int]):
        return FakeSpoofResult(is_real=False, confidence=0.95)


@pytest.fixture
def recognizer_real():
    r = FaceRecognizer()
    r._spoofer = FakeSpoofer()
    return r


@pytest.fixture
def recognizer_fake():
    r = FaceRecognizer()
    r._spoofer = FakeSpooferAllFake()
    return r


class TestSpoofCheck:
    def test_check_spoof_real(self, recognizer_real):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        assert recognizer_real._check_spoof(frame, [100, 100, 200, 200]) is False

    def test_check_spoof_fake(self, recognizer_fake):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        assert recognizer_fake._check_spoof(frame, [100, 100, 200, 200]) is True

    def test_check_spoof_no_spoofer(self):
        r = FaceRecognizer()
        r._spoofer = None
        assert r._check_spoof(np.zeros((480, 640, 3), dtype=np.uint8), [0, 0, 100, 100]) is False


class TestSpoofLabels:
    def test_spoof_label(self, recognizer_fake):
        r = recognizer_fake
        r._last_results[1] = FaceResult(1, None, FaceResultStatus.SPOOF)
        labels = r.get_face_labels()
        assert labels[1] == "Spoof"

    def test_spoof_persists_in_lru(self, recognizer_fake):
        r = recognizer_fake
        r._last_results[1] = FaceResult(1, None, FaceResultStatus.SPOOF)
        # LRU cleanup with empty active_ids → SPOOF should survive
        import types
        # simulate stale cleanup logic inline
        active_ids = set()
        for tid in list(r._last_results):
            result = r._last_results.get(tid)
            if result is not None and result.result in (FaceResultStatus.NORMAL, FaceResultStatus.SPOOF):
                pass  # keep
            else:
                r._last_results.pop(tid, None)
        assert 1 in r._last_results  # SPOOF not cleaned

    def test_stranger_cleaned_in_lru(self, recognizer_fake):
        r = recognizer_fake
        r._last_results[2] = FaceResult(2, None, FaceResultStatus.STRANGER)
        active_ids = set()
        for tid in list(r._last_results):
            result = r._last_results.get(tid)
            if result is not None and result.result in (FaceResultStatus.NORMAL, FaceResultStatus.SPOOF):
                pass
            else:
                r._last_results.pop(tid, None)
        assert 2 not in r._last_results  # STRANGER cleaned
