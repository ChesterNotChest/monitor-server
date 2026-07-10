"""ByteTrack-style person tracking for YOLO detections.

The production path may delegate to a third-party ByteTrack implementation when
available. A small IoU tracker is kept as a deterministic fallback so the
pipeline remains testable and usable before model/runtime packages are installed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto

from src.config import settings
from src.constants import YOLOEntityType
from src.service.vision_module.vision_types import Track

logger = logging.getLogger(__name__)

_MAX_MISSING_FRAMES = 30


class ByteTrackerState(Enum):
    IDLE = auto()
    ACTIVE = auto()


@dataclass
class _TrackedBox:
    bbox: list[float]
    track_id: int
    score: float
    missing_frames: int = 0


def _area(bbox: list[float]) -> float:
    x1, y1, x2, y2 = bbox
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _iou(left: list[float], right: list[float]) -> float:
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    ix1 = max(lx1, rx1)
    iy1 = max(ly1, ry1)
    ix2 = min(lx2, rx2)
    iy2 = min(ly2, ry2)
    intersection = _area([ix1, iy1, ix2, iy2])
    union = _area(left) + _area(right) - intersection
    return intersection / union if union > 0 else 0.0


class ByteTracker:
    """Assign stable track ids to YOLO person detections."""

    def __init__(
        self,
        track_thresh: float | None = None,
        match_thresh: float | None = None,
        max_missing_frames: int = _MAX_MISSING_FRAMES,
    ) -> None:
        self.track_thresh = settings.BYTETRACK_TRACK_THRESH if track_thresh is None else track_thresh
        self.match_thresh = settings.BYTETRACK_MATCH_THRESH if match_thresh is None else match_thresh
        self.max_missing_frames = max_missing_frames
        self._state = ByteTrackerState.IDLE
        self._next_track_id = 1
        self._tracks: dict[int, _TrackedBox] = {}
        self._external_tracker = self._load_external_tracker()

    @property
    def state(self) -> ByteTrackerState:
        return self._state

    def update(self, detections: list[object]) -> list[Track]:
        """Track YOLO person detections and return ``Track`` records."""

        person_detections = [
            det for det in detections
            if _is_person(det) and det.confidence >= self.track_thresh
        ]
        if not person_detections:
            self._age_tracks()
            self._state = ByteTrackerState.IDLE if not self._tracks else self._state
            return []

        self._state = ByteTrackerState.ACTIVE
        if self._external_tracker is not None:
            external = self._update_external(person_detections)
            if external is not None:
                return external

        return self._update_fallback(person_detections)

    def _update_fallback(self, detections: list[object]) -> list[Track]:
        unmatched_track_ids = set(self._tracks)
        assigned: list[Track] = []

        for det in detections:
            best_track_id: int | None = None
            best_iou = 0.0
            for track_id in list(unmatched_track_ids):
                score = _iou(det.bbox, self._tracks[track_id].bbox)
                if score > best_iou:
                    best_iou = score
                    best_track_id = track_id

            if best_track_id is not None and best_iou >= self.match_thresh:
                tracked = self._tracks[best_track_id]
                tracked.bbox = det.bbox
                tracked.score = det.confidence
                tracked.missing_frames = 0
                unmatched_track_ids.remove(best_track_id)
                track_id = best_track_id
            else:
                track_id = self._next_track_id
                self._next_track_id += 1
                self._tracks[track_id] = _TrackedBox(det.bbox, track_id, det.confidence)

            assigned.append(Track(bbox=det.bbox, track_id=track_id, score=det.confidence))

        for track_id in unmatched_track_ids:
            self._tracks[track_id].missing_frames += 1
        self._drop_stale_tracks()
        return assigned

    def _age_tracks(self) -> None:
        for tracked in self._tracks.values():
            tracked.missing_frames += 1
        self._drop_stale_tracks()

    def _drop_stale_tracks(self) -> None:
        stale = [
            track_id for track_id, tracked in self._tracks.items()
            if tracked.missing_frames > self.max_missing_frames
        ]
        for track_id in stale:
            del self._tracks[track_id]

    def _load_external_tracker(self) -> object | None:
        try:
            from bytetrack import BYTETracker  # type: ignore
        except Exception:
            return None
        try:
            return BYTETracker(
                track_thresh=self.track_thresh,
                match_thresh=self.match_thresh,
            )
        except Exception:
            logger.exception("Failed to initialize external BYTETracker; using fallback")
            return None

    def _update_external(self, detections: list[object]) -> list[Track] | None:
        # Different ByteTrack packages expose slightly different APIs. Until the
        # concrete dependency is pinned, unsupported signatures fall back to the
        # deterministic IoU tracker.
        try:
            import numpy as np

            det_array = np.array(
                [det.bbox + [det.confidence] for det in detections],
                dtype=float,
            )
            results = self._external_tracker.update(det_array)  # type: ignore[attr-defined]
        except Exception:
            return None

        tracks: list[Track] = []
        try:
            for item in results:
                if hasattr(item, "tlbr"):
                    bbox = list(item.tlbr)
                    track_id = int(item.track_id)
                    score = float(getattr(item, "score", 1.0))
                else:
                    bbox = list(item[:4])
                    track_id = int(item[4])
                    score = float(item[5] if len(item) > 5 else 1.0)
                tracks.append(Track(bbox=bbox, track_id=track_id, score=score))
        except Exception:
            logger.exception("Unsupported BYTETracker output; using fallback")
            return None
        return tracks


def _is_person(det: object) -> bool:
    return (
        getattr(det, "entity_type_id", None) == YOLOEntityType.PERSON
        or getattr(det, "class_id", None) == 0
    )
