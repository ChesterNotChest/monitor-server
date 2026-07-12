"""Service entry points for monitor View create/delete/query operations."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.schema.http.view_schema import ViewResponse


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

        # 等待 Node 推流就绪（收到 UPDATE_STREAM 后 ffmpeg 需要几秒启动）
        import time
        time.sleep(5)

        # 原始合流已禁用——AI 管线启动后会推送带标注的合流到 :1936。
        # 两个 ffmpeg 同时推同一直播流会互相覆盖。
        # merge_started, unavailable = start_merge(
        #     view.id,
        #     video_id,
        #     audio_id,
        #     video.name,
        #     audio.name,
        #     wait_for_inputs=False,
        # )
        # if not merge_started:
        #     warnings.append(
        #         "Raw stream(s) not ready for merge: " + ", ".join(unavailable)
        #     )

        # 启动 AI 推理管线（Part A YOLO + Part B ByteTrack/Face/Fence/SlowFast + Part C Alert/YAMNet）
        # 注意：必须在后台线程中启动，因为 start_pipeline 包含 YAMNet TensorFlow 模型
        # 加载（首次约 20s），若同步等待会阻塞 View 创建响应。
        # 使用专用线程 + 持久化事件循环，因为 asyncio.run() 在
        # start_pipeline 返回后会取消所有后台 Task。
        import asyncio
        import threading
        from src.service.vision_task import start_pipeline

        # 提前捕获字符串值——后台线程不能访问已关闭 session 的 ORM 对象
        _video_name = video.name
        _audio_name = audio.name

        async def _pipeline_forever(view_id: int, video_id: int, video_name: str,
                                    audio_id: int, audio_name: str) -> None:
            await start_pipeline(view_id, video_id, video_name, audio_id, audio_name)
            while True:
                await asyncio.sleep(3600)

        def _launch() -> None:
            asyncio.run(_pipeline_forever(view.id, video_id, _video_name,
                                          audio_id, _audio_name))

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(start_pipeline(view.id, video_id, _video_name,
                                            audio_id, _audio_name))
        except RuntimeError:
            threading.Thread(target=_launch, daemon=True).start()

        return ViewResponse(
            id=view.id,
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


def list_views(db: Session):
    """List all monitor Views."""

    from src.repository.monitor_view_repo import MonitorViewRepo

    return MonitorViewRepo(db).all()


def get_view(db: Session, view_id: int):
    """Return one monitor View by id."""

    from src.repository.monitor_view_repo import MonitorViewRepo

    return MonitorViewRepo(db).get(view_id)
