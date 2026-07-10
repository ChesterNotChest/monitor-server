"""
Debug 测试数据模块 —— 仅在 DEBUG_FLV_TRANSMIT=True 时启用。

启动时自动创建一套完整的测试数据链路：
  test_cassette/xxx.flv → recording → view → exception → alert/event

当告警被标记"已处理"后，录制文件被清理，60 秒内自动恢复。
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone

from src.config import settings
from src.extensions import SessionLocal

logger = logging.getLogger(__name__)

# 固定的测试数据 ID，避免 URL 变化
TEST_GROUP_ID = 9999
TEST_NODE_ID = 9999
TEST_VIDEO_DEVICE_ID = 9999
TEST_AUDIO_DEVICE_ID = 9999
TEST_VIEW_ID = 9999
TEST_EXCEPTION_ID = 9999
TEST_RECORDING_ID = 9999
TEST_ALERT_ID = 9999

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
    """创建测试数据链路。若数据已存在且完整则跳过。返回 True 表示成功。"""
    flv_path = _get_cassette_flv()
    if flv_path is None:
        logger.warning("[debug_data] test_cassette/ 中无 .flv 文件，跳过测试数据创建。"
                       "请放入一段 .flv 视频")
        return False

    db = SessionLocal()
    try:
        from src.models.node import Node
        from src.models.video_device import VideoDevice
        from src.models.audio_device import AudioDevice
        from src.models.alert_group import AlertGroup
        from src.models.exception import ExceptionDef
        from src.models.monitor_view import MonitorView
        from src.models.recording import Recording
        from src.models.situation_event import SituationEvent
        from src.constants import SeverityLevel

        # Check if complete test data already exists
        existing_alert = db.get(SituationEvent, TEST_ALERT_ID)
        existing_view = db.get(MonitorView, TEST_VIEW_ID)
        if existing_alert is not None and existing_view is not None:
            logger.debug("[debug_data] 测试数据已存在且完整，跳过创建")
            db.close()
            return True

        # Clean up partial data from previous failed attempts (order matters: FK deps)
        for model, test_id in [
            (SituationEvent, TEST_ALERT_ID),
            (Recording, TEST_RECORDING_ID),
            (MonitorView, TEST_VIEW_ID),
            (ExceptionDef, TEST_EXCEPTION_ID),
            (AlertGroup, TEST_GROUP_ID),
            (AudioDevice, TEST_AUDIO_DEVICE_ID),
            (VideoDevice, TEST_VIDEO_DEVICE_ID),
            (Node, TEST_NODE_ID),
        ]:
            obj = db.get(model, test_id)
            if obj is not None:
                db.delete(obj)
        db.flush()

        # Create fresh test data

        # Node
        node = Node(
            id=TEST_NODE_ID,
            token="debug-test-node-token",
            is_connected=True,
            last_seen=datetime.now(timezone.utc),
        )
        db.add(node)

        # Video device
        video = VideoDevice(
            id=TEST_VIDEO_DEVICE_ID,
            name="Debug Test Camera",
            node_id=TEST_NODE_ID,
            streaming=True,
        )
        db.add(video)

        # Audio device
        audio = AudioDevice(
            id=TEST_AUDIO_DEVICE_ID,
            name="Debug Test Microphone",
            node_id=TEST_NODE_ID,
            streaming=True,
        )
        db.add(audio)
        db.flush()

        # Alert group (required by exception, NOT NULL)
        group = AlertGroup(
            id=TEST_GROUP_ID,
            name="[DEBUG] 测试告警组",
        )
        db.add(group)
        db.flush()

        # View
        view = MonitorView(
            id=TEST_VIEW_ID,
            video_id=TEST_VIDEO_DEVICE_ID,
            audio_id=TEST_AUDIO_DEVICE_ID,
        )
        db.add(view)
        db.flush()

        # Recording — points to canned FLV file
        recording = Recording(
            id=TEST_RECORDING_ID,
            view_id=TEST_VIEW_ID,
            file_path=os.path.abspath(flv_path),
            start_time=datetime.now(timezone.utc),
        )
        db.add(recording)
        db.flush()

        # Exception
        exc = ExceptionDef(
            id=TEST_EXCEPTION_ID,
            name="[DEBUG] 测试异常 — 非法入侵",
            severity=SeverityLevel.WARNING,
            group_id=TEST_GROUP_ID,
        )
        db.add(exc)
        db.flush()

        # Alert / Event (same situation_events table)
        alert = SituationEvent(
            id=TEST_ALERT_ID,
            view_id=TEST_VIEW_ID,
            exception_id=TEST_EXCEPTION_ID,
            recording_id=TEST_RECORDING_ID,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(alert)

        db.commit()
        logger.info("[debug_data] 测试数据链路已创建 (view=%s, alert=%s, flv=%s)",
                     TEST_VIEW_ID, TEST_ALERT_ID, os.path.basename(flv_path))
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
                db.close()
                if alert is None or view is None:
                    logger.info("[debug_data] 检测到测试数据被清理，自动恢复中...")
                    create_test_data()
            except Exception:
                try:
                    db.close()
                except Exception:
                    pass
                create_test_data()
        except Exception as e:
            logger.warning("[debug_data] 恢复检查异常: %s", e)


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
