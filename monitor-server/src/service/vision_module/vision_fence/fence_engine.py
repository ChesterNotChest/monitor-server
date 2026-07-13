"""电子围栏检测引擎 —— ENTERED / EXITED / TOO_CLOSE。"""

from __future__ import annotations

from collections import defaultdict
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
    TOO_CLOSE = auto()


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
    safe_distance: int = 0
    entry_delay_seconds: int = 0


class FenceEngine:
    """评估行人轨迹与围栏的关系。"""

    def __init__(self, view_id: int, db: Session | None = None,
                 fences: Iterable[ElectronicFence | _FenceConfig] | None = None) -> None:
        self.view_id = view_id
        self._fences: list[_FenceConfig] = []
        self._fences_loaded_at: float = 0.0
        self._fences_ttl: float = 5.0
        self._states: defaultdict[tuple[int, int], FenceState] = defaultdict(lambda: FenceState.NOT_ENTERED)
        self._leave_counts: defaultdict[tuple[int, int], int] = defaultdict(int)
        self._entry_frames: defaultdict[tuple[int, int], int] = defaultdict(int)
        self._entry_start: dict[tuple[int, int], float] = {}  # 进入时间戳
        self._expanded: dict[int, list[tuple[float, float]]] = {}
        self._frame_count: int = 0

        if fences is not None:
            self._fences = [self._coerce_fence(f) for f in fences]
        elif db is not None:
            self.load_fences(db)

    @property
    def fence_polygons(self) -> list[list[tuple[float, float]]]:
        import time
        now = time.monotonic()
        if now - self._fences_loaded_at >= self._fences_ttl:
            from src.extensions import SessionLocal
            with SessionLocal() as db:
                self.load_fences(db)
            self._fences_loaded_at = now
        return [f.coords for f in self._fences]

    @property
    def expanded_polygons(self) -> list[list[tuple[float, float]]]:
        self.fence_polygons
        return [self._get_expanded(f) for f in self._fences if f.safe_distance > 0]

    def load_fences(self, db: Session) -> None:
        rows = db.scalars(select(ElectronicFence).where(ElectronicFence.view_id == self.view_id)).all()
        self._fences = [self._coerce_fence(r) for r in rows]
        self._expanded.clear()

    def _get_expanded(self, fence: _FenceConfig) -> list[tuple[float, float]]:
        """返回向外扩展 safe_distance 像素的多边形（缓存）。"""
        if fence.id not in self._expanded:
            self._expanded[fence.id] = _expand_polygon(fence.coords, fence.safe_distance)
        return self._expanded[fence.id]

    def check(self, tracks: list[Track], frame_timestamp: float) -> list[FenceEvent]:
        events: list[FenceEvent] = []
        self._frame_count += 1
        if self._frame_count % 75 == 0:
            import logging
            _log = logging.getLogger(__name__)
            active = {tid: s.name for (_, tid), s in self._states.items() if s != FenceState.NOT_ENTERED}
            inside_count = sum(1 for (_, tid), s in self._states.items() if s == FenceState.ENTERED)
            _log.info("[Fence] frame=%d tracks=%d fences=%d states_active=%d inside=%d states=%s",
                      self._frame_count, len(tracks), len(self._fences), len(active), inside_count, active)
        for fence in self._fences:
            expanded = self._get_expanded(fence) if fence.safe_distance > 0 else None
            for track in tracks:
                key = (fence.id, track.track_id)
                inside = _bbox_intersects_polygon(track.bbox, fence.coords)
                near = False
                if expanded and not inside:
                    near = _bbox_intersects_polygon(track.bbox, expanded)

                if inside:
                    self._leave_counts[key] = 0
                    if key not in self._entry_start:
                        self._entry_start[key] = frame_timestamp
                else:
                    self._leave_counts[key] += 1
                    self._entry_start.pop(key, None)

                current = self._states[key]

                # TOO_CLOSE 检测
                if near and current == FenceState.NOT_ENTERED:
                    self._states[key] = FenceState.TOO_CLOSE
                    events.append(FenceEvent(fence_id=fence.id, track_id=track.track_id,
                                              result=FenceEventResult.TOO_CLOSE, entered=True))
                elif not near and current == FenceState.TOO_CLOSE:
                    self._states[key] = FenceState.NOT_ENTERED
                    events.append(FenceEvent(fence_id=fence.id, track_id=track.track_id,
                                              result=FenceEventResult.TOO_CLOSE, entered=False))

                # ENTERED 检测（时间累计触发）
                if inside and current in (FenceState.NOT_ENTERED, FenceState.TOO_CLOSE):
                    entry_start = self._entry_start.get(key, frame_timestamp)
                    if frame_timestamp - entry_start >= fence.entry_delay_seconds:
                        self._states[key] = FenceState.ENTERED
                        events.append(FenceEvent(fence_id=fence.id, track_id=track.track_id,
                                                  result=FenceEventResult.ENTERED, entered=True))
                # EXITED 检测
                elif not inside and current == FenceState.ENTERED:
                    if self._leave_counts[key] >= fence.leave_frames:
                        self._states[key] = FenceState.NOT_ENTERED
                        events.append(FenceEvent(fence_id=fence.id, track_id=track.track_id,
                                                  result=FenceEventResult.ENTERED, entered=False))

        active_ids = {t.track_id for t in tracks}
        events.extend(self._cleanup_stale(active_ids, frame_timestamp))
        return events

    async def check_and_publish(self, tracks: list[Track], frame_timestamp: float) -> list[FenceEvent]:
        import time
        now = time.monotonic()
        if now - self._fences_loaded_at >= self._fences_ttl:
            from src.extensions import SessionLocal
            with SessionLocal() as db:
                self.load_fences(db)
            self._fences_loaded_at = now
        events = self.check(tracks, frame_timestamp)
        if events:
            pass  # events published to EventBus silently
            await event_bus.publish(FENCE, {
                "view_id": self.view_id,
                "fence_event_ids": [int(e.result) for e in events],  # 修复键名
                "fences": [{"fence_id": e.fence_id, "track_id": e.track_id,
                            "result": e.result.name, "result_id": int(e.result),
                            "entered": e.entered} for e in events],
            })
        return events

    def _drop_key(self, key: tuple[int, int]) -> None:
        self._states.pop(key, None)
        self._leave_counts.pop(key, None)
        self._entry_frames.pop(key, None)
        self._entry_start.pop(key, None)

    def _cleanup_stale(self, active_ids: set[int], ts: float) -> list[FenceEvent]:
        events: list[FenceEvent] = []
        for (fid, tid), state in list(self._states.items()):
            if tid in active_ids:
                continue
            fence = self._find_fence(fid)
            if fence is None:
                self._drop_key((fid, tid))
                continue
            if state == FenceState.ENTERED:
                events.append(FenceEvent(fence_id=fid, track_id=tid,
                                          result=FenceEventResult.ENTERED, entered=False))
            elif state == FenceState.TOO_CLOSE:
                events.append(FenceEvent(fence_id=fid, track_id=tid,
                                          result=FenceEventResult.TOO_CLOSE, entered=False))
            self._drop_key((fid, tid))
        return events

    def get_track_states(self) -> dict[int, str]:
        """返回 ENTERED/TOO_CLOSE 状态的 track 标签（供每帧标注用）。"""
        result: dict[int, str] = {}
        for (fid, tid), state in self._states.items():
            if state == FenceState.NOT_ENTERED:
                continue
            label = f"Fence-{fid}"
            if state == FenceState.TOO_CLOSE:
                label += ":TOO_CLOSE"
            elif state == FenceState.ENTERED:
                label += ":IN"
            result[tid] = label
        return result

    def _find_fence(self, fid: int) -> _FenceConfig | None:
        for f in self._fences:
            if f.id == fid:
                return f
        return None

    def _coerce_fence(self, fence) -> _FenceConfig:
        if isinstance(fence, _FenceConfig):
            return fence
        return _FenceConfig(
            id=fence.id, name=fence.name,
            coords=[(float(x), float(y)) for x, y in fence.coords],
            dwell_time=float(getattr(fence, "dwell_time", 10)),
            density=float(getattr(fence, "density", 0.6)),
            leave_frames=int(getattr(fence, "leave_frames", 5)),
            safe_distance=int(getattr(fence, "safe_distance", 0)),
            entry_delay_seconds=int(getattr(fence, "entry_delay_seconds", 0)),
        )


def _expand_polygon(coords: list[tuple[float, float]], dist: int) -> list[tuple[float, float]]:
    """向量外扩：将多边形每条边向外平移 dist 像素，取交点。"""
    if dist <= 0:
        return coords
    result: list[tuple[float, float]] = []
    n = len(coords)
    for i in range(n):
        p_prev = coords[(i - 1) % n]
        p_curr = coords[i]
        p_next = coords[(i + 1) % n]
        # 当前边方向 → 法向量（向外）
        e1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        e2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
        # 两条边的向外法向量
        n1 = _normalize((e1[1], -e1[0]))
        n2 = _normalize((e2[1], -e2[0]))
        # 平移后的两条线
        l1a = (p_prev[0] + n1[0] * dist, p_prev[1] + n1[1] * dist)
        l1b = (p_curr[0] + n1[0] * dist, p_curr[1] + n1[1] * dist)
        l2a = (p_curr[0] + n2[0] * dist, p_curr[1] + n2[1] * dist)
        l2b = (p_next[0] + n2[0] * dist, p_next[1] + n2[1] * dist)
        pt = _line_intersection(l1a, l1b, l2a, l2b)
        if pt:
            result.append(pt)
        else:
            result.append((p_curr[0] + (n1[0] + n2[0]) * dist / 2,
                           p_curr[1] + (n1[1] + n2[1]) * dist / 2))
    return result


def _normalize(v: tuple[float, float]) -> tuple[float, float]:
    import math
    length = math.sqrt(v[0] * v[0] + v[1] * v[1])
    if length == 0:
        return (0.0, 0.0)
    return (v[0] / length, v[1] / length)


def _line_intersection(a1, a2, b1, b2) -> tuple[float, float] | None:
    x1, y1 = a1; x2, y2 = a2; x3, y3 = b1; x4, y4 = b2
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def _bbox_intersects_polygon(bbox, polygon) -> bool:
    x1, y1, x2, y2 = bbox
    rect = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    if any(_point_in_polygon(p, polygon) for p in rect):
        return True
    if any(_point_in_rect(p, rect[0][0], rect[0][1], rect[2][0], rect[2][1]) for p in polygon):
        return True
    re = list(zip(rect, rect[1:] + rect[:1]))
    pe = list(zip(polygon, polygon[1:] + polygon[:1]))
    return any(_segments_intersect(a1, a2, b1, b2) for a1, a2 in re for b1, b2 in pe)


def _point_in_rect(pt, rx1, ry1, rx2, ry2) -> bool:
    return rx1 <= pt[0] <= rx2 and ry1 <= pt[1] <= ry2


def _point_in_polygon(pt, poly) -> bool:
    x, y = pt; inside = False; j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi):
            inside = not inside
        j = i
    return inside


def _segments_intersect(p1, p2, q1, q2) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    o1 = orient(p1, p2, q1); o2 = orient(p1, p2, q2)
    o3 = orient(q1, q2, p1); o4 = orient(q1, q2, p2)
    return (o1 == 0 or o2 == 0 or (o1 > 0) != (o2 > 0)) and (o3 == 0 or o4 == 0 or (o3 > 0) != (o4 > 0))
