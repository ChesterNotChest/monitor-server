"""Service entry points for monitor View create/delete/query operations."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.schema.http.view_schema import ViewResponse

logger = logging.getLogger(__name__)


def create_view(
    db: Session,
    audio_id: int,
    video_id: int,
) -> ViewResponse | None:
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

        urls = build_play_urls(view.id)
        db.commit()
        db.refresh(view)

        # 等待 Node 推流就绪
        import time
        time.sleep(5)

        # 启动 AI 推理管线
        try:
            import asyncio
            import threading
            from src.service.vision_task import start_pipeline, wait_pipeline_stopped

            _video_name = video.name
            _audio_name = audio.name

            async def _pipeline_forever(view_id: int, video_id: int, video_name: str,
                                        audio_id: int, audio_name: str) -> None:
                if await start_pipeline(view_id, video_id, video_name, audio_id, audio_name):
                    await wait_pipeline_stopped(view_id)

            def _launch() -> None:
                asyncio.run(_pipeline_forever(view.id, video_id, _video_name,
                                              audio_id, _audio_name))

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(start_pipeline(view.id, video_id, _video_name,
                                                audio_id, _audio_name))
            except RuntimeError:
                threading.Thread(target=_launch, daemon=True).start()
        except ImportError:
            warnings.append("AI pipeline unavailable — view will have no stream")

        return ViewResponse(
            id=view.id,
            name=view.name,
            audio_id=view.audio_id,
            video_id=view.video_id,
            cache_path=view.cache_path,
            created_at=view.created_at,
            flv_url=urls.get("flv_url"),
            webrtc_url=urls.get("webrtc_url"),
            rtmp_url=urls.get("rtmp_url"),
            warnings=warnings,
        )
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

        # 先清围栏——围栏生命周期包含于 View
        from sqlalchemy import select
        from src.repository.electronic_fence_repo import ElectronicFenceRepo
        from src.models.electronic_fence import ElectronicFence
        fence_repo = ElectronicFenceRepo(db)
        for fence in db.scalars(select(ElectronicFence).where(ElectronicFence.view_id == view_id)).all():
            fence_repo.delete(fence.id)

        # 级联删除告警
        from src.models.situation_event import SituationEvent
        from src.repository.situation_event_repo import SituationEventRepo
        from src.models.alert_review import AlertReview
        from src.repository.alert_review_repo import AlertReviewRepo
        event_repo = SituationEventRepo(db)
        review_repo = AlertReviewRepo(db)
        events = db.scalars(select(SituationEvent).where(SituationEvent.view_id == view_id)).all()
        for evt in events:
            for review in db.scalars(select(AlertReview).where(AlertReview.alert_id == evt.id)).all():
                review_repo.delete(review.id)
            event_repo.delete(evt.id)

        view_repo.delete(view_id)
        stop_merge(view_id)
        check_and_stop_stream(db, "video", video_id)
        check_and_stop_stream(db, "audio", audio_id)

        db.commit()

        # 停止 AI 推理管线
        import asyncio
        from src.service.vision_task import stop_pipeline
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(stop_pipeline(view_id))
        except RuntimeError:
            asyncio.run(stop_pipeline(view_id))

        return True
    except Exception:
        db.rollback()
        raise


def list_views(db: Session) -> list[ViewResponse]:
    """List all monitor Views with playback URLs."""

    from src.network.rtmp.pusher import build_play_urls
    from src.repository.monitor_view_repo import MonitorViewRepo

    views = MonitorViewRepo(db).all()
    return [
        ViewResponse(
            id=v.id,
            name=v.name,
            audio_id=v.audio_id,
            video_id=v.video_id,
            cache_path=v.cache_path,
            created_at=v.created_at,
            flv_url=build_play_urls(v.id).get("flv_url"),
            webrtc_url=build_play_urls(v.id).get("webrtc_url"),
            rtmp_url=build_play_urls(v.id).get("rtmp_url"),
            warnings=[],
        )
        for v in views
    ]


def get_view(db: Session, view_id: int) -> ViewResponse | None:
    """Return one monitor View by id with playback URLs."""

    from src.network.rtmp.pusher import build_play_urls
    from src.repository.monitor_view_repo import MonitorViewRepo

    view = MonitorViewRepo(db).get(view_id)
    if view is None:
        return None

    urls = build_play_urls(view.id)
    return ViewResponse(
        id=view.id,
        name=view.name,
        audio_id=view.audio_id,
        video_id=view.video_id,
        cache_path=view.cache_path,
        created_at=view.created_at,
        flv_url=urls.get("flv_url"),
        webrtc_url=urls.get("webrtc_url"),
        rtmp_url=urls.get("rtmp_url"),
        warnings=[],
    )
