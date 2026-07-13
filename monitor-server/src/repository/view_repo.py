"""监控视图数据访问。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import MonitorView


def create(db: Session, audio_id: int | None, video_id: int) -> MonitorView:
    view = MonitorView(audio_id=audio_id, video_id=video_id)
    db.add(view)
    db.commit()
    db.refresh(view)
    return view


def delete(db: Session, view_id: int) -> MonitorView | None:
    view = get_by_id(db, view_id)
    if view is None:
        return None

    db.delete(view)
    db.commit()
    return view


def get_all(db: Session) -> list[MonitorView]:
    return list(db.scalars(select(MonitorView)).all())


def get_by_id(db: Session, view_id: int) -> MonitorView | None:
    return db.get(MonitorView, view_id)


def count_by_video_id(db: Session, video_id: int) -> int:
    stmt = select(func.count()).select_from(MonitorView).where(MonitorView.video_id == video_id)
    return int(db.scalar(stmt) or 0)


def count_by_audio_id(db: Session, audio_id: int) -> int:
    stmt = select(func.count()).select_from(MonitorView).where(MonitorView.audio_id == audio_id)
    return int(db.scalar(stmt) or 0)
