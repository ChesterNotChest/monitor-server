from datetime import date, datetime
from src.constants import SeverityLevel
from src.models.situation_event import SituationEvent
from src.repository.alert_group_repo import AlertGroupRepo
from src.repository.audio_device_repo import AudioDeviceRepo
from src.repository.exception_def_repo import ExceptionDefRepo
from src.repository.monitor_view_repo import MonitorViewRepo
from src.repository.node_repo import NodeRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.service.report_task import get_daily_report, get_deepseek_daily_report


def _seed_view(db):
    node = NodeRepo(db).create(token="daily-report-node")
    video = VideoDeviceRepo(db).create(name="daily-cam", node_id=node.id)
    audio = AudioDeviceRepo(db).create(name="daily-mic", node_id=node.id)
    return MonitorViewRepo(db).create(video_id=video.id, audio_id=audio.id)


def test_daily_report_empty(db):
    report = get_daily_report(db, date(2026, 7, 12))

    assert report["date"] == "2026-07-12"
    assert report["total_alerts"] == 0
    assert report["risk_level"] == "LOW"
    assert report["by_severity"] == []
    assert report["hourly_trend"] == []


def test_daily_report_summarizes_alerts(db):
    view = _seed_view(db)
    group = AlertGroupRepo(db).create(name="daily-report-group")
    exc = ExceptionDefRepo(db).create(
        name="Fence intrusion",
        severity=SeverityLevel.CRITICAL,
        group_id=group.id,
    )
    db.add(SituationEvent(
        view_id=view.id,
        exception_id=exc.id,
        timestamp=datetime(2026, 7, 12, 9, 30, 0),
    ))
    db.add(SituationEvent(
        view_id=view.id,
        exception_id=exc.id,
        timestamp=datetime(2026, 7, 12, 9, 45, 0),
    ))
    db.commit()

    report = get_daily_report(db, date(2026, 7, 12))

    assert report["total_alerts"] == 2
    assert report["risk_level"] == "HIGH"
    assert report["by_severity"] == [{"label": "CRITICAL", "value": 2}]
    assert report["top_exceptions"][0] == {"label": "Fence intrusion", "value": 2}
    assert report["hourly_trend"] == [{"hour": "09:00", "count": 2}]
    assert report["key_findings"]
    assert report["recommendations"]


def test_deepseek_daily_report_uses_model_text(db, monkeypatch):
    calls = []

    def fake_call_deepseek(api_key, model, local_report):
        calls.append((api_key, model, local_report))
        return {
            "summary": "DeepSeek 生成的日报摘要。",
            "key_findings": ["模型发现一"],
            "recommendations": ["模型建议一"],
        }

    monkeypatch.setattr("src.service.report_task._call_deepseek_report_model", fake_call_deepseek)

    report = get_deepseek_daily_report(db, "sk-test", date(2026, 7, 12), "deepseek-v4-flash")

    assert report["summary"] == "DeepSeek 生成的日报摘要。"
    assert report["key_findings"] == ["模型发现一"]
    assert report["recommendations"] == ["模型建议一"]
    assert report["ai_provider"] == "deepseek"
    assert report["ai_model"] == "deepseek-v4-flash"
    assert report["ai_generated"] is True
    assert calls[0][0] == "sk-test"
    assert calls[0][1] == "deepseek-v4-flash"
