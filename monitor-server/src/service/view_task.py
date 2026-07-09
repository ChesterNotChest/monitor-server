"""Service entry points for monitor View create/delete/query operations."""

from __future__ import annotations

from sqlalchemy.orm import Session


def create_view(
    db: Session,
    audio_id: int,
    video_id: int,
) -> dict | None:
    """Create a monitor View and persist its lifecycle changes."""

    from src.network.rtmp.pusher import build_play_urls
    from src.repository.audio_device_repo import AudioDeviceRepo
    from src.repository.monitor_view_repo import MonitorViewRepo
    from src.repository.video_device_repo import VideoDeviceRepo
    from src.service.view_module.ffmpeg_manager import start_merge
    from src.service.view_module.lifecycle import check_and_start_stream

    try:
        video_repo = VideoDeviceRepo(db)
        audio_repo = AudioDeviceRepo(db)
        view_repo = MonitorViewRepo(db)

        video = video_repo.get(video_id)
        audio = audio_repo.get(audio_id)
        if video is None or audio is None:
            db.rollback()
            return None

        warnings: list[str] = []
        if not check_and_start_stream(db, "video", video_id):
            warnings.append(f"Video device {video_id} stream already in use or unavailable")
        if not check_and_start_stream(db, "audio", audio_id):
            warnings.append(f"Audio device {audio_id} stream already in use or unavailable")

        view = view_repo.create(audio_id=audio_id, video_id=video_id)

        merge_started, unavailable = start_merge(
            view.id,
            video_id,
            audio_id,
            video.name,
            audio.name,
        )
        if not merge_started:
            warnings.append(
                "Raw stream(s) not ready for merge: " + ", ".join(unavailable)
            )

        urls = build_play_urls(view.id)
        db.commit()
        db.refresh(view)

        return {
            "view": view,
            "srs_urls": urls,
            "warnings": warnings,
        }
    except Exception:
        db.rollback()
        raise


def delete_view(db: Session, view_id: int) -> bool:
    """Delete a monitor View and persist stream release changes."""

    from src.repository.monitor_view_repo import MonitorViewRepo
    from src.service.view_module.ffmpeg_manager import stop_merge
    from src.service.view_module.lifecycle import check_and_stop_stream

    try:
        view_repo = MonitorViewRepo(db)
        view = view_repo.get(view_id)
        if view is None:
            db.rollback()
            return False

        video_id = view.video_id
        audio_id = view.audio_id

        view_repo.delete(view_id)
        stop_merge(view_id)
        check_and_stop_stream(db, "video", video_id)
        check_and_stop_stream(db, "audio", audio_id)

        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def list_views(db: Session):
    """List all monitor Views."""

    from src.repository.monitor_view_repo import MonitorViewRepo

    return MonitorViewRepo(db).all()


def get_view(db: Session, view_id: int):
    """Return one monitor View by id."""

    from src.repository.monitor_view_repo import MonitorViewRepo

    return MonitorViewRepo(db).get(view_id)
