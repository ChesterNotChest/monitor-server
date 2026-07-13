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

_MIN_FACE_CROP_SIZE = 50

# ── 已知人脸库版本号（API 层写入 → 识别层读取，触发动态重载）──
_face_db_version: int = 0
# TTL 兜底重载间隔（秒）：即使无 API 通知，也定期重载以覆盖外部变更
_FACE_DB_RELOAD_TTL: float = 30.0


def notify_face_db_changed() -> None:
    """命名人物 CRUD 完成后调用，标记已知人脸库已过期。"""
    global _face_db_version
    _face_db_version += 1


class FaceResultStatus(Enum):
    NO_RESULT = auto()
    STRANGER = auto()
    NORMAL = auto()


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
    ) -> None:
        self.tolerance = settings.FACE_MATCH_TOLERANCE if tolerance is None else tolerance
        self.skip_frames = max(1, settings.FACE_SKIP_FRAMES if skip_frames is None else skip_frames)
        self._known_encodings: list[np.ndarray] = []
        self._known_names: list[str] = []
        self._last_results: dict[int, FaceResult] = {}
        self._frame_counter = 0
        self._face_lib = self._load_face_recognition()
        self._loaded_version: int = -1  # 强制首帧重载
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

    def load_known_people(self, db: Session) -> None:
        """Load NamedPerson 128D encodings into memory.

        ``NamedPerson.feat_json_id`` is treated flexibly: it may contain a JSON
        array directly or point to a JSON file containing the vector.
        """

        self._known_encodings.clear()
        self._known_names.clear()
        for person in NamedPersonRepo(db).all(limit=10_000):
            encoding = self._extract_encoding(person)
            if encoding is None:
                continue
            self._known_encodings.append(encoding)
            self._known_names.append(person.name)

    def _ensure_known_people(self) -> None:
        """版本号变化或 TTL 过期时从 DB 重载已知人脸库。"""
        global _face_db_version
        now = time.monotonic()
        if self._loaded_version == _face_db_version and (now - self._last_load_time) < _FACE_DB_RELOAD_TTL:
            return
        from src.extensions import SessionLocal
        with SessionLocal() as db:
            self.load_known_people(db)
        self._loaded_version = _face_db_version
        self._last_load_time = now

    def recognize(self, frame: np.ndarray, tracks: list[Track]) -> list[FaceResult]:
        self._frame_counter += 1
        self._ensure_known_people()

        # 1. 已缓存的 track 直接返回（同一个人不重复识别）
        uncached = [t for t in tracks if t.track_id not in self._last_results]

        if not uncached:
            return [self._last_results[t.track_id] for t in tracks]

        # 2. 跳帧：非识别帧只返回已有缓存
        if self._frame_counter % self.skip_frames != 1:
            return [self._last_results[t.track_id] for t in tracks
                    if t.track_id in self._last_results]

        # 3. 识别帧 — 只处理未缓存的人
        for track in uncached:
            result = self._recognize_track(frame, track)
            if result is not None and result.result != FaceResultStatus.NO_RESULT:
                self._last_results[track.track_id] = result

        # 4. LRU 清理 — 删除已离开画面的 track，超过上限时淘汰最旧条目
        active_ids = {t.track_id for t in tracks}
        stale = [tid for tid in self._last_results if tid not in active_ids]
        for tid in stale:
            self._last_results.pop(tid, None)
        # 上限保护（防止异常场景下累积）
        _MAX_LAST = 512
        if len(self._last_results) > _MAX_LAST:
            overflow = sorted(self._last_results.keys())[:len(self._last_results) - _MAX_LAST]
            for tid in overflow:
                self._last_results.pop(tid, None)

        return [self._last_results[t.track_id] for t in tracks
                if t.track_id in self._last_results]

    async def recognize_and_publish(
        self,
        frame: np.ndarray,
        tracks: list[Track],
        view_id: int,
    ) -> list[FaceResult]:
        results = self.recognize(frame, tracks)
        if results:
            await event_bus.publish(
                FACE,
                {
                    "view_id": view_id,
                    "faces": [
                        {
                            "track_id": result.track_id,
                            "person_name": result.person_name,
                            "result": result.result.name,
                            "result_id": int(result.result_id),
                        }
                        for result in results
                    ],
                    "labels": self.get_face_labels(),
                },
            )
        return results

    _last_logged_labels: dict[int, str] = {}

    def get_face_labels(self) -> dict[int, str]:
        labels: dict[int, str] = {}
        for track_id, result in self._last_results.items():
            if result.result == FaceResultStatus.NORMAL and result.person_name:
                labels[track_id] = result.person_name
            elif result.result == FaceResultStatus.STRANGER:
                labels[track_id] = "Stranger"
        # 只在标签集合变化时输出（降噪）
        if labels != self._last_logged_labels:
            if labels:
                logger.info("[Face] labels: %s", labels)
            self._last_logged_labels = dict(labels)
        return labels

    def _recognize_track(self, frame: np.ndarray, track: Track) -> FaceResult | None:
        logger.debug("[Face] track %d: START crop", track.track_id)
        crop = _crop(frame, track.bbox)
        if crop is None:
            logger.debug("[Face] track %d: crop failed", track.track_id)
            return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)
        height, width = crop.shape[:2]
        if width < _MIN_FACE_CROP_SIZE or height < _MIN_FACE_CROP_SIZE:
            logger.debug("[Face] track %d: crop too small %dx%d (min %d)",
                          track.track_id, width, height, _MIN_FACE_CROP_SIZE)
            return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)

        if self._face_lib is None:
            logger.warning("[Face] track %d: face_lib not loaded", track.track_id)
            return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)

        logger.debug("[Face] track %d: rgb_crop %dx%d", track.track_id, width, height)
        rgb_crop = np.ascontiguousarray(crop[:, :, ::-1])
        try:
            logger.debug("[Face] track %d: calling face_locations", track.track_id)
            locations = self._face_lib.face_locations(rgb_crop)
            logger.debug("[Face] track %d: face_locations done, found=%d", track.track_id, len(locations))
            if not locations:
                logger.debug("[Face] track %d: no face_locations found in %dx%d crop",
                              track.track_id, width, height)
                return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)
            logger.debug("[Face] track %d: calling face_encodings", track.track_id)
            encodings = self._face_encodings(rgb_crop, locations)
            logger.debug("[Face] track %d: face_encodings done, count=%d", track.track_id, len(encodings))
            if not encodings:
                logger.debug("[Face] track %d: face found but encoding failed", track.track_id)
                return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)
        except Exception:
            logger.exception("Face recognition failed for track %s", track.track_id)
            return FaceResult(track.track_id, None, FaceResultStatus.NO_RESULT)

        if not self._known_encodings:
            logger.debug("[Face] track %d: STRANGER (no known people in DB)", track.track_id)
            return FaceResult(track.track_id, None, FaceResultStatus.STRANGER)

        encoding = encodings[0]
        logger.debug("[Face] track %d: comparing against %d known", track.track_id, len(self._known_encodings))
        matches = self._face_lib.compare_faces(
            self._known_encodings,
            encoding,
            tolerance=self.tolerance,
        )
        logger.debug("[Face] track %d: compare done, matched=%s", track.track_id, any(matches))
        if not any(matches):
            logger.debug("[Face] track %d: STRANGER", track.track_id)
            return FaceResult(track.track_id, None, FaceResultStatus.STRANGER)

        match_index = matches.index(True)
        logger.info("[Face] track %d: NAMED %s", track.track_id, self._known_names[match_index])
        return FaceResult(track.track_id, self._known_names[match_index], FaceResultStatus.NORMAL)

    def _face_encodings(self, rgb_crop: np.ndarray, locations: list[tuple[int, int, int, int]]) -> list[np.ndarray]:
        try:
            logger.debug("[Face] _face_encodings with locations, crop=%s", rgb_crop.shape)
            return self._face_lib.face_encodings(rgb_crop, locations)
        except TypeError as exc:
            logger.debug("[Face] _face_encodings TypeError, retrying without locations: %s", exc)
            if "compute_face_descriptor" not in str(exc) and "incompatible function arguments" not in str(exc):
                raise
            logger.warning(
                "face_recognition location-bound encoding is incompatible; retrying without locations"
            )
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
