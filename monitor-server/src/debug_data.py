"""
Debug 测试数据模块 —— 仅在 DEBUG_FLV_TRANSMIT=True 时启用。

启动时自动创建一套完整的测试数据链路：
  test_cassette/xxx.flv → recording → view → exception → alert/event

当告警被标记"已处理"后，录制文件被清理，60 秒内自动恢复。
"""

import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timezone

from src.config import settings
from src.extensions import SessionLocal, engine, Base

logger = logging.getLogger(__name__)

# 固定的测试数据 ID，避免 URL 变化
TEST_NODE_ID = 1
TEST_VIDEO_DEVICE_ID = 1
TEST_AUDIO_DEVICE_ID = 1
TEST_VIEW_ID = 1
TEST_EXCEPTION_ID = 1
TEST_RECORDING_ID = 1
TEST_ALERT_ID = 1

CASSETTE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test_cassette")
RECOVERY_INTERVAL = 60  # seconds

_timer_started = False


def _get_cassette_flv() -> str | None:
    """返回 test_cassette 目录中第一个 .flv 文件路径，没有则返回 None。"""
    os.makedirs(CASSETTE_DIR, exist_ok=True)
    for f in sorted(os.listdir(CASSETTE_DIR)):
        if f.endswith(".flv"):
            return os.path.join(CASSETTE_DIR, f)
    return None


def create_test_data() -> bool:
    """创建测试数据链路。若数据已存在则跳过。返回 True 表示创建成功或已存在。"""
    flv_path = _get_cassette_flv()
    if flv_path is None:
        logger.warning("[debug_data] test_cassette/ 中无 .flv 文件，跳过测试数据创建。"
                       "请放入一段 .flv 视频（可用 FFmpeg 生成："
                       "ffmpeg -f lavfi -i testsrc=duration=30:size=640x480:rate=30 -f flv test.flv）")
        return False

    db = SessionLocal()
    try:
        from src.models.node import Node
        from src.models.video_device import VideoDevice
        from src.models.audio_device import AudioDevice
        from src.models.monitor_view import MonitorView
        from src.models.exception import ExceptionDef
        from src.models.situation_event import SituationEvent
        from src.models.recording import Recording

        # Check if all test data already exists
        existing_view = db.get(MonitorView, TEST_VIEW_ID)
        if existing_view is not None:
            # Seed log entries independently (always, not gated by view existence)
            from src.models.log_entry import LogEntry
            existing_logs = db.query(LogEntry).count()
            if existing_logs == 0:
                sample_logs = [
                    LogEntry(log_type=1, severity=1, summary="[DEBUG] 系统启动完成", created_at=datetime.now(timezone.utc)),
                    LogEntry(log_type=2, severity=2, summary="[DEBUG] 检测到测试异常: 非法入侵", view_id=TEST_VIEW_ID, event_id=TEST_ALERT_ID, created_at=datetime.now(timezone.utc)),
                    LogEntry(log_type=3, severity=3, summary="[DEBUG] 告警已触发: 围栏闯入", view_id=TEST_VIEW_ID, event_id=TEST_ALERT_ID, created_at=datetime.now(timezone.utc)),
                    LogEntry(log_type=1, severity=1, summary="[DEBUG] 用户 admin 登录系统", operator_id=1, created_at=datetime.now(timezone.utc)),
                ]
                for l in sample_logs:
                    db.add(l)
                db.commit()
                logger.info("[debug_data] ✓ 测试日志已创建 (4 条)")
            return True

        # Node
        node = db.get(Node, TEST_NODE_ID)
        if node is None:
            node = Node(
                id=TEST_NODE_ID,
                token="debug-test-node-token",
                is_connected=True,
                last_seen=datetime.now(timezone.utc),
            )
            db.add(node)
            db.flush()

        # Video device
        video = db.get(VideoDevice, TEST_VIDEO_DEVICE_ID)
        if video is None:
            video = VideoDevice(
                id=TEST_VIDEO_DEVICE_ID,
                name="Debug Test Camera",
                node_id=TEST_NODE_ID,
                streaming=True,
            )
            db.add(video)
            db.flush()

        # Audio device
        audio = db.get(AudioDevice, TEST_AUDIO_DEVICE_ID)
        if audio is None:
            audio = AudioDevice(
                id=TEST_AUDIO_DEVICE_ID,
                name="Debug Test Microphone",
                node_id=TEST_NODE_ID,
                streaming=True,
            )
            db.add(audio)
            db.flush()

        # Recording
        recording = db.get(Recording, TEST_RECORDING_ID)
        if recording is None:
            recording = Recording(
                id=TEST_RECORDING_ID,
                view_id=TEST_VIEW_ID,
                file_path=os.path.abspath(flv_path),
                start_time=datetime.now(timezone.utc),
            )
            db.add(recording)
            db.flush()

        # View — 指向 debug TXRX 的 flv_url
        from src.network.rtmp.pusher import build_play_urls
        play_urls = build_play_urls(TEST_VIEW_ID)
        flv_url = play_urls.get("flv_url") or f"http://localhost:{settings.SRS_HTTP_PORT}/view/{TEST_VIEW_ID}.flv"

        view = MonitorView(
            id=TEST_VIEW_ID,
            video_id=TEST_VIDEO_DEVICE_ID,
            audio_id=TEST_AUDIO_DEVICE_ID,
            cache_path=None,
        )
        db.add(view)
        db.flush()

        # Alert group (required by exception, NOT NULL)
        from src.models.alert_group import AlertGroup
        TEST_GROUP_ID = 1
        group = db.get(AlertGroup, TEST_GROUP_ID)
        if group is None:
            group = AlertGroup(
                id=TEST_GROUP_ID,
                name="[DEBUG] 测试告警组",
            )
            db.add(group)
            db.flush()

        # Exception
        from src.constants import SeverityLevel
        exc = db.get(ExceptionDef, TEST_EXCEPTION_ID)
        if exc is None:
            exc = ExceptionDef(
                id=TEST_EXCEPTION_ID,
                name="[DEBUG] 测试异常 — 非法入侵",
                severity=SeverityLevel.WARNING,
                group_id=TEST_GROUP_ID,
            )
            db.add(exc)
            db.flush()

        # Alert / Event
        alert = db.get(SituationEvent, TEST_ALERT_ID)
        if alert is None:
            alert = SituationEvent(
                id=TEST_ALERT_ID,
                view_id=TEST_VIEW_ID,
                exception_id=TEST_EXCEPTION_ID,
                recording_id=TEST_RECORDING_ID,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(alert)
            db.flush()

        # Log entries — seed sample data for log center
        from src.models.log_entry import LogEntry
        existing_logs = db.query(LogEntry).count()
        if existing_logs == 0:
            sample_logs = [
                LogEntry(log_type=1, severity=1, summary="[DEBUG] 系统启动完成", created_at=datetime.now(timezone.utc)),
                LogEntry(log_type=2, severity=2, summary="[DEBUG] 检测到测试异常: 非法入侵", view_id=TEST_VIEW_ID, event_id=TEST_ALERT_ID, created_at=datetime.now(timezone.utc)),
                LogEntry(log_type=3, severity=3, summary="[DEBUG] 告警已触发: 围栏闯入", view_id=TEST_VIEW_ID, event_id=TEST_ALERT_ID, created_at=datetime.now(timezone.utc)),
                LogEntry(log_type=1, severity=1, summary="[DEBUG] 用户 admin 登录系统", operator_id=1, created_at=datetime.now(timezone.utc)),
            ]
            for l in sample_logs:
                db.add(l)

        db.commit()
        logger.info("[debug_data] ✓ 测试数据链路已创建 (view=%s, exception=%s, alert=%s, flv=%s)",
                     TEST_VIEW_ID, TEST_EXCEPTION_ID, TEST_ALERT_ID, os.path.basename(flv_path))
        return True

    except Exception as e:
        db.rollback()
        logger.error("[debug_data] 创建测试数据失败: %s", e)
        return False
    finally:
        db.close()


def _recovery_loop():
    """后台定时器：每 60 秒检查测试数据是否被清理，若是则重建。"""
    while True:
        time.sleep(RECOVERY_INTERVAL)
        try:
            db = SessionLocal()
            try:
                from src.models.situation_event import SituationEvent
                from src.models.monitor_view import MonitorView
                alert = db.get(SituationEvent, TEST_ALERT_ID)
                view = db.get(MonitorView, TEST_VIEW_ID)
                if alert is None or view is None:
                    logger.info("[debug_data] 检测到测试数据被清理，自动恢复中...")
                    db.close()
                    create_test_data()
                else:
                    db.close()
            except Exception:
                db.close()
                create_test_data()
        except Exception as e:
            logger.warning("[debug_data] 恢复检查异常: %s", e)


_synthetic_procs: list[subprocess.Popen] = []


def _start_synthetic_streams():
    """为 debug 设备启动合成测试流 → SRS。

    用 ffmpeg testsrc 模拟摄像头、sine 模拟麦克风，
    推到 SRS 的 /live/video_1 和 /live/audio_1。
    """
    import shutil
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    rtmp_base = f"rtmp://{settings.RTMP_HOST}:{settings.RTMP_PORT}/live"

    # 合成视频流
    video_cmd = [
        ffmpeg, "-re",
        "-f", "lavfi", "-i", "testsrc=duration=86400:size=640x480:rate=15",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=86400",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "flv",
        f"{rtmp_base}/Debug_Test_Camera_video_{TEST_VIDEO_DEVICE_ID}",
        "-y",
    ]
    try:
        p = subprocess.Popen(video_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _synthetic_procs.append(p)
        logger.info("[debug_data] ✓ 合成视频流已启动 → %s/live/Debug_Test_Camera_video_%s",
                     rtmp_base, TEST_VIDEO_DEVICE_ID)
    except FileNotFoundError:
        logger.warning("[debug_data] ffmpeg 未找到，无法启动合成视频流")

    # 合成音频流
    audio_cmd = [
        ffmpeg, "-re",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=86400",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "flv",
        f"{rtmp_base}/Debug_Test_Microphone_audio_{TEST_AUDIO_DEVICE_ID}",
        "-y",
    ]
    try:
        p = subprocess.Popen(audio_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _synthetic_procs.append(p)
        logger.info("[debug_data] ✓ 合成音频流已启动 → %s/live/Debug_Test_Microphone_audio_%s",
                     rtmp_base, TEST_AUDIO_DEVICE_ID)
    except FileNotFoundError:
        logger.warning("[debug_data] ffmpeg 未找到，无法启动合成音频流")

    # 等待流就绪后启动视图合流
    time.sleep(8)
    _start_view_merge(ffmpeg, rtmp_base)


def _start_view_merge(ffmpeg: str, rtmp_base: str):
    """为测试视图启动 ffmpeg 合流（拉取合成流 → 合并 → 推送视图路径）。"""
    view_push = f"rtmp://{settings.SRS_HOST}:{settings.SRS_RTMP_PORT}/live/{TEST_VIEW_ID}"
    video_pull = f"{rtmp_base}/Debug_Test_Camera_video_{TEST_VIDEO_DEVICE_ID}"
    audio_pull = f"{rtmp_base}/Debug_Test_Microphone_audio_{TEST_AUDIO_DEVICE_ID}"

    merge_cmd = [
        ffmpeg, "-re",
        "-i", video_pull, "-i", audio_pull,
        "-c:v", "copy", "-c:a", "aac",
        "-f", "flv", view_push, "-y",
    ]
    try:
        p = subprocess.Popen(merge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _synthetic_procs.append(p)
        logger.info("[debug_data] ✓ 视图合流已启动 → %s", view_push)
    except FileNotFoundError:
        logger.warning("[debug_data] ffmpeg 未找到，无法启动视图合流")


def start_debug_data():
    """启动 debug 测试数据（若配置开启）。"""
    global _timer_started
    if not settings.DEBUG_FLV_TRANSMIT:
        return

    logger.warning("=" * 50)
    logger.warning("  DEBUG_FLV_TRANSMIT 已启用")
    logger.warning("  测试数据将在每次标记'已处理'后 60 秒自动恢复")
    logger.warning("=" * 50)

    ok = create_test_data()
    if ok and not _timer_started:
        _timer_started = True
        t = threading.Thread(target=_recovery_loop, daemon=True, name="debug-data-recovery")
        t.start()
        logger.info("[debug_data] 自动恢复定时器已启动 (间隔 %ss)", RECOVERY_INTERVAL)

    # 启动合成测试流（每次重启都启动，不依赖视图是否已存在）
    _start_synthetic_streams()
