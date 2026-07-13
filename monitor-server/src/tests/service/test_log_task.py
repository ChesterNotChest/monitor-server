"""log_task 服务层测试。"""

import json

from src.constants import LogType, SeverityLevel
from src.repository.alert_group_repo import AlertGroupRepo
from src.repository.audio_device_repo import AudioDeviceRepo
from src.repository.exception_def_repo import ExceptionDefRepo
from src.repository.log_entry_repo import LogEntryRepo
from src.repository.monitor_view_repo import MonitorViewRepo
from src.repository.node_repo import NodeRepo
from src.repository.situation_event_repo import SituationEventRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.service import log_task


def _create_alert_event(db):
    node = NodeRepo(db).create(token="log-alert-node")
    video = VideoDeviceRepo(db).create(name="log-alert-cam", node_id=node.id)
    audio = AudioDeviceRepo(db).create(name="log-alert-mic", node_id=node.id)
    view = MonitorViewRepo(db).create(video_id=video.id, audio_id=audio.id)
    group = AlertGroupRepo(db).create(name="log-alert-group")
    exc = ExceptionDefRepo(db).create(
        name="人员出现",
        severity=SeverityLevel.WARNING,
        group_id=group.id,
    )
    event = SituationEventRepo(db).create(view_id=view.id, exception_id=exc.id)
    return event, exc


def test_record_alert_event_creates_log_entry(db):
    event, exc = _create_alert_event(db)

    entry = log_task.record_alert_event(db, event=event, exception_def=exc, recording_id=123)
    db.flush()

    logs = LogEntryRepo(db).all()
    assert len(logs) == 1
    assert entry.log_type == int(LogType.ALERT)
    assert entry.view_id == event.view_id
    assert entry.event_id == event.id
    assert entry.severity == int(SeverityLevel.WARNING)
    assert entry.summary == "告警触发：人员出现"

    details = json.loads(entry.details_json)
    assert details["action"] == "triggered"
    assert details["exception_name"] == "人员出现"
    assert details["recording_id"] == 123
