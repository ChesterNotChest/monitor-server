"""View Task 门户 —— 监控视图的创建、删除、查询。

此模块是 View 管理的主要入口点，协调 Repository、FFmpeg、推流生命周期。
"""

from sqlalchemy.orm import Session


def create_view(
    db: Session,
    audio_id: int,
    video_id: int,
) -> dict:
    """创建监控视图。

    内部逻辑（关键函数）：
    1. 验证设备存在
    2. 检查设备是否已被占用（warnings）
    3. 创建 MonitorView 记录
    4. 启动 FFmpeg 合流
    5. 返回响应（含播放 URL 和 warnings）
    """
    from src.repository.video_device_repo import VideoDeviceRepo
    from src.repository.audio_device_repo import AudioDeviceRepo
    from src.repository.monitor_view_repo import MonitorViewRepo
    from src.service.view_module.lifecycle import check_and_start_stream
    from src.service.view_module.ffmpeg_manager import start_merge
    from src.network.rtmp.pusher import build_play_urls

    video_repo = VideoDeviceRepo(db)
    audio_repo = AudioDeviceRepo(db)
    view_repo = MonitorViewRepo(db)

    # 1. 验证设备存在
    vd = video_repo.get(video_id)
    ad = audio_repo.get(audio_id)
    if vd is None or ad is None:
        return None  # caller 返回 404

    # 2. 检查占用
    warnings: list[str] = []
    if not check_and_start_stream(db, "video", video_id):
        warnings.append(f"Video device {video_id} stream already in use by another view")
    if not check_and_start_stream(db, "audio", audio_id):
        warnings.append(f"Audio device {audio_id} stream already in use by another view")

    # 3. 创建 View
    view = view_repo.create(audio_id=audio_id, video_id=video_id)

    # 4. 启动 FFmpeg
    start_merge(view.id, video_id, audio_id)

    # 5. 构建播放 URL
    urls = build_play_urls(view.id)

    return {
        "view": view,
        "srs_urls": urls,
        "warnings": warnings,
    }


def delete_view(db: Session, view_id: int) -> bool:
    """删除监控视图。

    DB 优先，FFmpeg 后杀：
    1. 查 View 是否存在
    2. 先删 DB 记录（事务保护）
    3. 杀 FFmpeg 子进程
    4. 检查是否需要停止设备推流
    """
    from src.repository.monitor_view_repo import MonitorViewRepo
    from src.service.view_module.lifecycle import check_and_stop_stream
    from src.service.view_module.ffmpeg_manager import stop_merge

    view_repo = MonitorViewRepo(db)
    view = view_repo.get(view_id)
    if view is None:
        return False

    video_id = view.video_id
    audio_id = view.audio_id

    # 1. 先删 DB
    view_repo.delete(view_id)

    # 2. 杀 FFmpeg（失败仅记日志）
    stop_merge(view_id)

    # 3. 检查释放推流
    check_and_stop_stream(db, "video", video_id)
    check_and_stop_stream(db, "audio", audio_id)

    return True


def list_views(db: Session):
    """列出所有监控视图。"""
    from src.repository.monitor_view_repo import MonitorViewRepo
    return MonitorViewRepo(db).all()


def get_view(db: Session, view_id: int):
    """获取单个监控视图详情。"""
    from src.repository.monitor_view_repo import MonitorViewRepo
    return MonitorViewRepo(db).get(view_id)
