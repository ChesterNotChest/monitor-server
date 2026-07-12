"""电子围栏服务。"""

from sqlalchemy.orm import Session

from src.repository.electronic_fence_repo import ElectronicFenceRepo


def list_fences(db: Session):
    return ElectronicFenceRepo(db).all()


def create_fence(db: Session, *, name: str, view_id: int,
                  coords: str, dwell_time: int = 10,
                  density: float = 0.6, leave_frames: int = 5):
    fence = ElectronicFenceRepo(db).create(
        name=name, view_id=view_id, coords=coords,
        dwell_time=dwell_time, density=density, leave_frames=leave_frames,
    )
    db.commit()
    return fence


def update_fence(db: Session, fence_id: int, coords: str):
    fence = ElectronicFenceRepo(db).update(fence_id, coords=coords)
    if fence is not None:
        db.commit()
    return fence


def delete_fence(db: Session, fence_id: int) -> bool:
    ok = ElectronicFenceRepo(db).delete(fence_id)
    if ok:
        db.commit()
    return ok
