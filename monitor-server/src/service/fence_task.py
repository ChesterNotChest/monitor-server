"""电子围栏服务。"""

import json
from sqlalchemy.orm import Session

from src.repository.electronic_fence_repo import ElectronicFenceRepo


def list_fences(db: Session):
    return ElectronicFenceRepo(db).all()


def create_fence(
    db: Session,
    *,
    name: str,
    view_id: int,
    coords: list[list[float]],
    dwell_time: int = 10,
    density: float = 0.6,
    leave_frames: int = 5,
    safe_distance: int = 0,
    entry_delay_seconds: int = 0,
):
    fence = ElectronicFenceRepo(db).create(
        name=name,
        view_id=view_id,
        coords=coords,
        dwell_time=dwell_time,
        density=density,
        leave_frames=leave_frames,
        safe_distance=safe_distance,
        entry_delay_seconds=entry_delay_seconds,
    )
    db.commit()
    return fence


def update_fence(
    db: Session,
    fence_id: int,
    *,
    name: str | None = None,
    view_id: int | None = None,
    coords: list[list[float]] | None = None,
    dwell_time: int | None = None,
    density: float | None = None,
    leave_frames: int | None = None,
    safe_distance: int | None = None,
    entry_delay_seconds: int | None = None,
):
    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if view_id is not None:
        kwargs["view_id"] = view_id
    if coords is not None:
        kwargs["coords"] = coords
    if dwell_time is not None:
        kwargs["dwell_time"] = dwell_time
    if density is not None:
        kwargs["density"] = density
    if leave_frames is not None:
        kwargs["leave_frames"] = leave_frames
    if safe_distance is not None:
        kwargs["safe_distance"] = safe_distance
    if entry_delay_seconds is not None:
        kwargs["entry_delay_seconds"] = entry_delay_seconds
    fence = ElectronicFenceRepo(db).update(fence_id, **kwargs)
    return fence


def delete_fence(db: Session, fence_id: int) -> bool:
    ok = ElectronicFenceRepo(db).delete(fence_id)
    if ok:
        db.commit()
    return ok
