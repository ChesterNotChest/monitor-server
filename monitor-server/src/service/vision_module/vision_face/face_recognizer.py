"""Face recognition over ByteTrack person crops."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Iterable

import numpy as np
from sqlalchemy.orm import Session

from src.config import settings
from src.constants import FaceRecognitionResult
from src.models.named_person import NamedPerson
from src.repository.named_person_repo import NamedPersonRepo
from src.service.vision_module.vision_event_bus import FACE, event_bus
from src.service.vision_module.vision_types import Track

logger = logging.getLogger(__name__)

_MIN_FACE_CROP_SIZE = 80  # 太小的人脸编码不可靠，跳过

# ── 已知人脸库版本号 ──
_face_db_version: int = 0
_FACE_DB_RELOAD_TTL: float = 30.0


def notify_face_db_changed() -> None:
    """命名人物 CRUD 完成后调用，标记已知人脸库已过期。"""
    global _face_db_version
    _face_db_version += 1


class FaceResultStatus(Enum):
    NO_RESULT = auto()
    STRANGER = auto()
    NORMAL = auto()
    SPOOF = auto()  # 假脸（照片/屏幕）


@dataclass
class FaceResult:
    track_id: int
    person_name: str | None
    result: FaceResultStatus

    @property
    def result_id(self) -> int:
        return {
            FaceResultStatus.NO_RESULT: FaceRecognitionResult.NO_RESULT,
            FaceResultStatus.STRANGER: FaceRecognitionResult.STRANGER,
            FaceResultStatus.NORMAL: FaceRecognitionResult.NORMAL,
            FaceResultStatus.SPOOF: FaceRecognitionResult.SPOOF,
        }[self.result]


class FaceRecognizer:
    """Recognize known people from tracked person crops."""

    def __init__(
        self,
        db: Session | None = None,
        *,
        known_people: Iterable[tuple[np.ndarray, str]] | None = None,
        tolerance: float | None = None,
        skip_frames: int | None = None,
        enable_spoof: bool = True,
    ) -> None:
        self.tolerance = settings.FACE_MATCH_TOLERANCE if tolerance is None else tolerance
        self.skip_frames = max(1, settings.FACE_SKIP_FRAMES if skip_frames is None else skip_frames)
        self._known_encodings: list[np.ndarray] = []
        self._known_names: list[str] = []
        self._last_results: dict[int, FaceResult] = {}
        self._named_confirm: dict[int, int] = {}
        self._stranger_confirm: dict[int, int] = {}  # track → 连续 Stranger 帧数
        self._spoof_count: dict[int, int] = {}  # track → 连续 Spoof 帧数
        self._frame_counter = 0
        self._face_lib = self._load_face_recognition()
        self._spoofer = self._load_spoofer() if enable_spoof else None
        self._loaded_version: int = -1
        self._last_load_time: float = 0.0

        if known_people is not None:
            for encoding, name in known_people:
                self._known_encodings.append(np.asarray(encoding, dtype=float))
                self._known_names.append(name)
            self._loaded_version = _face_db_version
            self._last_load_time = time.monotonic()
        elif db is not None:
            self.load_known_people(db)
            self._loaded_version = _face_db_version
            self._last_load_time = time.monotonic()

    # ── Spoofer ──────────────────────────────────

    def _load_spoofer(self) -> object | None:
        try:
            from uniface.spoofing import MiniFASNet
            model = MiniFASNet()
            logger.info("MiniFASNet anti-spoofing model loaded")
            return model
        except Exception:
            logger.warning("uniface not installed; spoof detection disabled")
            return None

    # ── Known people ─────────────────────────────

    def load_known_people(self, db: Session) -> None:
        self._known_encodings.clear()
        self._known_names.clear()
        for person in NamedPersonRepo(db).all(limit=10_000):
            encoding = self._extract_encoding(person)
            if encoding is None:
                continue
            self._known_encodings.append(encoding)
            self._known_names.append(person.name)

    def _ensure_known_people(self) -> None:
        global _face_db_version
        now = time.monotonic()
        if self._loaded_version == _face_db_version and (now - self._last_load_time) < _FACE_DB_RELOAD_TTL:
            return
        from src.extensions import SessionLocal
        with SessionLocal() as db:
            self.load_known_people(db)
        self._loaded_version = _face_db_version
        self._last_load_time = now

    # ── Main loop ────────────────────────────────

    def recognize(self, frame: np.ndarray, tracks: list[Track]) -> list[FaceResult]:
        self._frame_counter += 1
        self._ensure_known_people()

        _is_recognition_frame = (self._frame_counter % self.skip_frames == 1)

        # 1. 已缓存的 track 直接返回
        uncached = [t for t in tracks if t.track_id not in self._last_results]
        if not uncached:
            return [self._last_results[t.track_id] for t in tracks]

        # 2. 跳帧
        if not _is_recognition_frame:
            return [self._last_results[t.track_id] for t in tracks
                    if t.track_id in self._last_results]

        # 3. Spoof 检查 — 对所有非 SPOOF track 跑，每帧上限防拥堵
        if self._spoofer is not None:
            _spoof_confirmed: set[int] = {
                tid for tid, r in self._last_results.items()
                if r.result == FaceResultStatus.SPOOF
            }
            logger.debug("[dbg] spoof: total=%d confirmed=%d", len(tracks), len(_spoof_confirmed))
            _spoof_processed = 0
            for track in tracks:
                if track.track_id in _spoof_confirmed:
                    continue
                x1, y1, x2, y2 = track.bbox
                if (x2 - x1) < _MIN_FACE_CROP_SIZE or (y2 - y1) < _MIN_FACE_CROP_SIZE:
                    continue  # 太小 → 不做 spoof
                if _spoof_processed >= 3:
                    break
                _spoof_processed += 1
                if self._check_spoof(frame, track.bbox):
                    self._spoof_count[track.track_id] = self._spoof_count.get(track.track_id, 0) + 1
                    if self._spoof_count[track.track_id] >= 3:
                        result = FaceResult(track.track_id, None, FaceResultStatus.SPOOF)
                        self._last_results[track.track_id] = result
                        self._spoof_count.pop(track.track_id, None)
                        logger.warning("[Face] track %d: SPOOF confirmed", track.track_id)
                else:
                    self._spoof_count.pop(track.track_id, None)  # 一帧不是就重置

        # 4. 人脸识别 — 仅 uncached + 非 SPOOF（每帧上限防突发拥堵）
        _MAX_FACES_PER_FRAME = 2
        _processed = 0
        for track in uncached:
            if _processed >= _MAX_FACES_PER_FRAME:
                break
            # SPOOF 已确认的不重复识别
            cached = self._last_results.get(track.track_id)
            if cached is not None and cached.result == FaceResultStatus.SPOOF:
                continue
            result = self._recognize_track(frame, track)
            _processed += 1
            if result is None or result.result == FaceResultStatus.NO_RESULT:
                self._named_confirm.pop(track.track_id, None)
                self._stranger_confirm.pop(track.track_id, None)
                continue
            if result.person_name:
                c = self._named_confirm.get(track.track_id, 0) + 1
                self._named_confirm[track.track_id] = c
                logger.debug("[dbg] track %d NAMED confirm=%d/2 name=%s", track.track_id, c, result.person_name)
                if c >= 2:
                    self._last_results[track.track_id] = result
                    self._named_confirm.pop(track.track_id, None)
                    logger.info("[dbg] track %d NAMED locked: %s", track.track_id, result.person_name)
            else:
                # STRANGER: 需 2 次确认防误报
                c = self._stranger_confirm.get(track.track_id, 0) + 1
                self._stranger_confirm[track.track_id] = c
                logger.debug("[dbg] track %d STRANGER confirm=%d/2", track.track_id, c)
                if c >= 2:
                    self._last_results[track.track_id] = result
                    self._stranger_confirm.pop(track.track_id, None)
                    logger.info("[dbg] track %d STRANGER locked", track.track_id)
                self._named_confirm.pop(track.track_id, None)

        # 5. LRU 清理
        active_ids = {t.track_id for t in tracks}
        stale = [tid for tid in self._last_results if tid not in active_ids]
        for tid in stale:
            result = self._last_results.get(tid)
            if result is not None and result.result in (FaceResultStatus.NORMAL, FaceResultStatus.SPOOF):
                pass
            else:
                self._last_results.pop(tid, None)
                self._named_confirm.pop(tid, None)
                self._stranger_confirm.pop(tid, None)
                self._spoof_count.pop(tid, None)
        _MAX_LAST = 512
        if len(self._last_results) > _MAX_LAST:
            overflow = sorted(self._last_results.keys())[:len(self._last_results) - _MAX_LAST]
            for tid in overflow:
                self._last_results.pop(tid, None)

        return [self._last_results[t.track_id] for t in tracks
                if t.track_id in self._last_results]

    # ── Spoof check ──────────────────────────────

    _SPOOF_CONFIDENCE_THRESHOLD = 0.7  # fake confidence > 0.7 才判为假脸

    def _check_spoof(self, frame: np.ndarray, bbox: list[float]) -> bool:
        """MiniFASNet 单帧假脸检测。用 confidence 阈值替代模型内部 is_real。"""
        if self._spoofer is None:
            return False
        try:
            x1, y1, x2, y2 = [int(round(v)) for v in bbox]
            result = self._spoofer.predict(frame, (x1, y1, x2, y2))
            fake_conf = 1.0 - result.confidence if result.is_real else result.confidence
            if fake_conf > self._SPOOF_CONFIDENCE_THRESHOLD:
                logger.info("[Face] SPOOF fake_conf=%.3f > %.2f", fake_conf, self._SPOOF_CONFIDENCE_THRESHOLD)
                return True
            return False
        except Exception:
            logger.debug("MiniFASNet prediction failed", exc_info=True)
            return False

    # ── Face recognition ─────────────────────────

    def _recognize_track(self, frame: np.ndarray, track: Track) -> FaceResult | None:
        crop = _crop(frame, track.bbox)
        if crop is None:
            return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)
        height, width = crop.shape[:2]
        if width < _MIN_FACE_CROP_SIZE or height < _MIN_FACE_CROP_SIZE:
            return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)

        if self._face_lib is None:
            return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)

        rgb_crop = np.ascontiguousarray(crop[:, :, ::-1])
        try:
            locations = self._face_lib.face_locations(rgb_crop)
            if not locations:
                return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)
            encodings = self._face_encodings(rgb_crop, locations)
            if not encodings:
                return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)
        except Exception:
            logger.exception("Face recognition failed for track %s", track.track_id)
            return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)

        if not self._known_encodings:
            return FaceResult(track.track_id, None, FaceResultStatus.STRANGER)

        encoding = encodings[0]
        matches = self._face_lib.compare_faces(
            self._known_encodings, encoding, tolerance=self.tolerance,
        )
        if not any(matches):
            return FaceResult(track.track_id, None, FaceResultStatus.STRANGER)

        match_index = matches.index(True)
        logger.info("[Face] track %d: NAMED %s", track.track_id, self._known_names[match_index])
        return FaceResult(track.track_id, self._known_names[match_index], FaceResultStatus.NORMAL)

    # ── Labels ───────────────────────────────────

    _last_logged_labels: dict[int, str] = {}

    def get_face_labels(self) -> dict[int, str]:
        labels: dict[int, str] = {}
        for track_id, result in self._last_results.items():
            if result.result == FaceResultStatus.SPOOF:
                labels[track_id] = "Spoof"
            elif result.result == FaceResultStatus.NORMAL and result.person_name:
                labels[track_id] = result.person_name
            elif result.result == FaceResultStatus.STRANGER:
                labels[track_id] = "Stranger"
        if labels != self._last_logged_labels:
            if labels:
                logger.info("[Face] labels: %s", labels)
            self._last_logged_labels = dict(labels)
        return labels

    # ── Event bus ────────────────────────────────

    async def recognize_and_publish(
        self, frame: np.ndarray, tracks: list[Track], view_id: int,
    ) -> list[FaceResult]:
        results = self.recognize(frame, tracks)
        if results:
            await event_bus.publish(FACE, {
                "view_id": view_id,
                "faces": [
                    {
                        "track_id": r.track_id,
                        "person_name": r.person_name,
                        "result": r.result.name,
                        "result_id": int(r.result_id),
                    }
                    for r in results
                ],
                "labels": self.get_face_labels(),
            })
        return results

    # ── Internals ────────────────────────────────

    def _face_encodings(self, rgb_crop: np.ndarray, locations: list[tuple[int, int, int, int]]) -> list[np.ndarray]:
        try:
            return self._face_lib.face_encodings(rgb_crop, locations)
        except TypeError as exc:
            if "compute_face_descriptor" not in str(exc) and "incompatible function arguments" not in str(exc):
                raise
            logger.warning("face_recognition location-bound encoding incompatible; retrying without")
            return self._face_lib.face_encodings(rgb_crop)

    def _extract_encoding(self, person: NamedPerson) -> np.ndarray | None:
        raw = person.feat_json_id
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            path = Path(raw)
            if not path.exists():
                return None
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                logger.exception("Failed to load face encoding for %s", person.name)
                return None
        try:
            vector = np.asarray(payload, dtype=float)
        except Exception:
            return None
        return vector if vector.shape == (128,) else None

    def _load_face_recognition(self) -> object | None:
        try:
            import face_recognition  # type: ignore
        except Exception:
            logger.warning("face_recognition is not installed; face module returns NO_RESULT")
            return None
        return face_recognition


def _crop(frame: np.ndarray, bbox: list[float]) -> np.ndarray | None:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = [int(round(value)) for value in bbox]
    x1 = max(0, min(width, x1))
    x2 = max(0, min(width, x2))
    y1 = max(0, min(height, y1))
    y2 = max(0, min(height, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2]
