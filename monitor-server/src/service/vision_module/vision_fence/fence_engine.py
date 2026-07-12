"""Electronic fence intersection and dwell logic."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants import FenceEventResult
from src.models.electronic_fence import ElectronicFence
from src.service.vision_module.vision_event_bus import FENCE, event_bus
from src.service.vision_module.vision_types import Track


class FenceState(Enum):
    NOT_ENTERED = auto()
    ENTERED = auto()


@dataclass
class FenceEvent:
    fence_id: int
    track_id: int
    result: FenceEventResult
    entered: bool


@dataclass
class _FenceConfig:
    id: int
    name: str
    coords: list[tuple[float, float]]
    dwell_time: float
    density: float
    leave_frames: int


class FenceEngine:
    """Evaluate person tracks against fences bound to a View."""

    def __init__(
        self,
        view_id: int,
        db: Session | None = None,
        fences: Iterable[ElectronicFence | _FenceConfig] | None = None,
    ) -> None:
        self.view_id = view_id
        self._fences: list[_FenceConfig] = []
        self._fences_loaded_at: float = 0.0
        self._fences_ttl: float = 5.0  # 5 秒重载一次围栏
        self._windows: defaultdict[tuple[int, int], deque[tuple[float, bool]]] = defaultdict(deque)
        self._states: defaultdict[tuple[int, int], FenceState] = defaultdict(lambda: FenceState.NOT_ENTERED)
        self._leave_counts: defaultdict[tuple[int, int], int] = defaultdict(int)

        if fences is not None:
            self._fences = [self._coerce_fence(fence) for fence in fences]
        elif db is not None:
            self.load_fences(db)

    @property
    def fence_polygons(self) -> list[list[tuple[float, float]]]:
        """Return all fence polygon coordinates for drawing. TTL auto-reload."""
        import time
        import logging
        _logger = logging.getLogger(__name__)
        _now = time.monotonic()
        if _now - self._fences_loaded_at >= self._fences_ttl:
            from src.extensions import SessionLocal
            with SessionLocal() as db:
                self.load_fences(db)
            self._fences_loaded_at = _now
            _logger.info("[Fence] TTL reload: %d fence(s) loaded for view %d",
                          len(self._fences), self.view_id)
        return [fence.coords for fence in self._fences]

    def load_fences(self, db: Session) -> None:
        rows = db.scalars(
            select(ElectronicFence).where(ElectronicFence.view_id == self.view_id),
        ).all()
        self._fences = [self._coerce_fence(row) for row in rows]

    def check(self, tracks: list[Track], frame_timestamp: float) -> list[FenceEvent]:
        events: list[FenceEvent] = []
        for fence in self._fences:
            for track in tracks:
                key = (fence.id, track.track_id)
                overlapped = _bbox_intersects_polygon(track.bbox, fence.coords)
                self._append_window(key, fence, frame_timestamp, overlapped)

                if overlapped:
                    self._leave_counts[key] = 0
                else:
                    self._leave_counts[key] += 1

                if self._states[key] == FenceState.NOT_ENTERED:
                    if self._density(key) >= fence.density:
                        self._states[key] = FenceState.ENTERED
                        events.append(FenceEvent(
                            fence_id=fence.id,
                            track_id=track.track_id,
                            result=FenceEventResult.ENTERED,
                            entered=True,
                        ))
                elif self._leave_counts[key] >= fence.leave_frames:
                    self._states[key] = FenceState.NOT_ENTERED
                    self._leave_counts[key] = 0
                    events.append(FenceEvent(
                        fence_id=fence.id,
                        track_id=track.track_id,
                        result=FenceEventResult.ENTERED,
                        entered=False,
                    ))
        return events

    async def check_and_publish(
        self,
        tracks: list[Track],
        frame_timestamp: float,
    ) -> list[FenceEvent]:
        # 5 秒缓存：围栏配置低频变更，不必每帧查 DB
        import time
        _now = time.monotonic()
        if _now - self._fences_loaded_at >= self._fences_ttl:
            from src.extensions import SessionLocal
            with SessionLocal() as db:
                self.load_fences(db)
            self._fences_loaded_at = _now
        events = self.check(tracks, frame_timestamp)
        if events:
            await event_bus.publish(
                FENCE,
                {
                    "view_id": self.view_id,
                    "fences": [
                        {
                            "fence_id": event.fence_id,
                            "track_id": event.track_id,
                            "result": event.result.name,
                            "result_id": int(event.result),
                            "entered": event.entered,
                        }
                        for event in events
                    ],
                },
            )
        return events

    def _append_window(
        self,
        key: tuple[int, int],
        fence: _FenceConfig,
        timestamp: float,
        overlapped: bool,
    ) -> None:
        window = self._windows[key]
        window.append((timestamp, overlapped))
        min_timestamp = timestamp - fence.dwell_time
        while window and window[0][0] < min_timestamp:
            window.popleft()

    def _density(self, key: tuple[int, int]) -> float:
        window = self._windows[key]
        if not window:
            return 0.0
        return sum(1 for _, value in window if value) / len(window)

    def _coerce_fence(self, fence: ElectronicFence | _FenceConfig) -> _FenceConfig:
        if isinstance(fence, _FenceConfig):
            return fence
        return _FenceConfig(
            id=fence.id,
            name=fence.name,
            coords=[(float(x), float(y)) for x, y in fence.coords],
            dwell_time=float(fence.dwell_time),
            density=float(fence.density),
            leave_frames=int(fence.leave_frames),
        )


def _bbox_intersects_polygon(bbox: list[float], polygon: list[tuple[float, float]]) -> bool:
    x1, y1, x2, y2 = bbox
    rect = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    if any(_point_in_polygon(point, polygon) for point in rect):
        return True
    if any(_point_in_rect(point, bbox) for point in polygon):
        return True
    rect_edges = list(zip(rect, rect[1:] + rect[:1]))
    poly_edges = list(zip(polygon, polygon[1:] + polygon[:1]))
    return any(_segments_intersect(a1, a2, b1, b2) for a1, a2 in rect_edges for b1, b2 in poly_edges)


def _point_in_rect(point: tuple[float, float], bbox: list[float]) -> bool:
    x, y = point
    x1, y1, x2, y2 = bbox
    return x1 <= x <= x2 and y1 <= y <= y2


def _point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
        ):
            inside = not inside
        j = i
    return inside


def _segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    q1: tuple[float, float],
    q2: tuple[float, float],
) -> bool:
    def orient(a, b, c) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    o1 = orient(p1, p2, q1)
    o2 = orient(p1, p2, q2)
    o3 = orient(q1, q2, p1)
    o4 = orient(q1, q2, p2)
    return (o1 == 0 or o2 == 0 or (o1 > 0) != (o2 > 0)) and (
        o3 == 0 or o4 == 0 or (o3 > 0) != (o4 > 0)
    )
