"""log_task 服务层冒烟测试。"""

from src.service.log_task import LogService, query_logs, stats_by_log_type, stats_by_severity
from src.constants import LogType, SeverityLevel


class TestLogService:
    def test_write_device_log(self, db):
        entry = LogService.write(
            db, LogType.DEVICE, summary="摄像头A 上线",
            details={"device_type": "video", "device_id": 1, "event": "online"},
        )
        assert entry.id is not None
        assert entry.log_type == LogType.DEVICE
        assert entry.summary == "摄像头A 上线"

    def test_write_operation_log(self, db):
        entry = LogService.write(
            db, LogType.OPERATION,
            summary="删除命名人物 张三",
            details={"action": "delete_person", "target_type": "named_person", "target_name": "张三"},
        )
        assert entry.log_type == LogType.OPERATION

    def test_write_recognition_log(self, db):
        entry = LogService.write(
            db, LogType.RECOGNITION,
            summary="YOLO 检测到 PERSON",
            details={"model": "YOLO", "detected": "PERSON", "confidence": 0.95},
        )
        assert entry.log_type == LogType.RECOGNITION

    def test_write_alert_log(self, db):
        entry = LogService.write(
            db, LogType.ALERT,
            summary="确认告警: 入侵检测",
            details={"action": "confirm", "comment": "已通知安保"},
        )
        assert entry.log_type == LogType.ALERT

    def test_write_system_log(self, db):
        entry = LogService.write(
            db, LogType.SYSTEM, severity=SeverityLevel.INFO,
            summary="服务启动",
            details={"event": "startup"},
        )
        assert entry.log_type == LogType.SYSTEM

    def test_write_without_details(self, db):
        entry = LogService.write(db, LogType.DEVICE, summary="仅摘要，无详情")
        assert entry.details_json is None


class TestLogQuery:
    def test_query_by_log_type(self, db):
        LogService.write(db, LogType.DEVICE, summary="设备1在线")
        LogService.write(db, LogType.OPERATION, summary="操作1")
        items, total = query_logs(db, log_type=LogType.DEVICE)
        assert total >= 1
        assert all(i.log_type == LogType.DEVICE for i in items)

    def test_query_empty(self, db):
        items, total = query_logs(db)
        assert isinstance(items, list)

    def test_stats(self, db):
        LogService.write(db, LogType.DEVICE, summary="d1")
        LogService.write(db, LogType.DEVICE, summary="d2")
        LogService.write(db, LogType.ALERT, summary="a1")
        rows = stats_by_log_type(db)
        assert isinstance(rows, list)
