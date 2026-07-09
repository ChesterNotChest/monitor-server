"""电子围栏服务。"""

from sqlalchemy.orm import Session

from src.repository.electronic_fence_repo import ElectronicFenceRepo


def list_fences(db: Session):
    return ElectronicFenceRepo(db).all()


def create_fence(db: Session, coords: str):
    return ElectronicFenceRepo(db).create(coords=coords)


def update_fence(db: Session, fence_id: int, coords: str):
    fence = ElectronicFenceRepo(db).update(fence_id, coords=coords)
    return fence


def delete_fence(db: Session, fence_id: int) -> bool:
    return ElectronicFenceRepo(db).delete(fence_id)
