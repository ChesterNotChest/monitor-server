"""Repository 层集成测试 —— 多 Repo 协作场景。"""

import pytest

from src.repository.node_repo import NodeRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.repository.audio_device_repo import AudioDeviceRepo
from src.repository.monitor_view_repo import MonitorViewRepo
from src.repository.alert_group_repo import AlertGroupRepo
from src.repository.exception_def_repo import ExceptionDefRepo
from src.repository.response_action_repo import ResponseActionRepo
from src.repository.entity_type_repo import EntityTypeRepo
from src.repository.action_type_repo import ActionTypeRepo
from src.repository.sound_type_repo import SoundTypeRepo
from src.repository.situation_event_repo import SituationEventRepo
from src.models.exception import exception_entities, exception_actions, exception_sounds
from src.constants import SeverityLevel


class TestViewLifecycle:
    """View 生命周期集成测试：创建 → 设备占用 → 删除 → 设备释放。"""

    def test_view_lifecycle_device_occupation(self, db):
        # 1. 创建基础设施
        node = NodeRepo(db).create(token="integration-token")
        video = VideoDeviceRepo(db).create(name="int-cam", node_id=node.id)
        audio = AudioDeviceRepo(db).create(name="int-mic", node_id=node.id)
        view_repo = MonitorViewRepo(db)

        # 2. 设备未被占用
        assert view_repo.device_in_use(video_id=video.id) is False
        assert view_repo.device_in_use(audio_id=audio.id) is False

        # 3. 创建 View → 设备被占用
        view = view_repo.create(video_id=video.id, audio_id=audio.id)
        assert view_repo.device_in_use(video_id=video.id) is True
        assert view_repo.device_in_use(audio_id=audio.id) is True

        # 4. 同一视频设备可被多个 View 使用（非独占）
        view2 = view_repo.create(video_id=video.id, audio_id=audio.id)
        assert view_repo.device_in_use(video_id=video.id) is True
        found_views = view_repo.find_by_device(video_id=video.id)
        assert len(found_views) == 2

        # 5. 删除 view2 → 视频设备仍被 view 占用
        view_repo.delete(view2.id)
        assert view_repo.device_in_use(video_id=video.id) is True

        # 6. 删除 view → 全部释放
        view_repo.delete(view.id)
        assert view_repo.device_in_use(video_id=video.id) is False
        assert view_repo.device_in_use(audio_id=audio.id) is False

    def test_video_only_view_is_accepted(self, db):
        """View 允许仅绑定视频（audio_id 可为 NULL）。"""
        node = NodeRepo(db).create(token="video-only-node")
        video = VideoDeviceRepo(db).create(name="solo-cam", node_id=node.id)
        view_repo = MonitorViewRepo(db)

        view = view_repo.create(video_id=video.id, audio_id=None)
        assert view is not None
        assert view.audio_id is None
        assert view.video_id == video.id


class TestExceptionAssociationIntegration:
    """异常定义 + 多对多关联（Entity/Action/Sound）集成测试。"""

    def test_exception_full_association_flow(self, db):
        # 1. 创建基础枚举
        ag = AlertGroupRepo(db).create(name="集成测试分组")
        entity = EntityTypeRepo(db).create(name="person")
        action = ActionTypeRepo(db).create(name="falling")
        sound = SoundTypeRepo(db).create(name="scream")

        # 2. 创建异常定义
        exc_repo = ExceptionDefRepo(db)
        exc = exc_repo.create(name="集成测试异常", severity=SeverityLevel.EMERGENCY, group_id=ag.id)

        # 3. 建立多对多关联
        db.execute(exception_entities.insert().values(exception_id=exc.id, entity_id=entity.id))
        db.execute(exception_actions.insert().values(exception_id=exc.id, action_id=action.id))
        db.execute(exception_sounds.insert().values(exception_id=exc.id, sound_id=sound.id))
        db.flush()

        # 4. 验证 with_details 加载
        results = exc_repo.with_details()
        found = [e for e in results if e.id == exc.id]
        assert len(found) == 1
        f = found[0]
        assert len(f.entities) == 1
        assert f.entities[0].name == "person"
        assert len(f.actions) == 1
        assert f.actions[0].name == "falling"
        assert len(f.sounds) == 1
        assert f.sounds[0].name == "scream"
        assert f.alert_group.name == "集成测试分组"


class TestAlertGroupResponseIntegration:
    """告警分组 + 响应动作多对多集成测试。"""

    def test_group_response_association(self, db):
        ag_repo = AlertGroupRepo(db)
        ra_repo = ResponseActionRepo(db)

        ag = ag_repo.create(name="紧急响应组")
        ra1 = ra_repo.create(name="trigger_recording")
        ra2 = ra_repo.create(name="send_notification")

        from src.models.response_action import alert_group_responses
        db.execute(alert_group_responses.insert().values(group_id=ag.id, response_id=ra1.id))
        db.execute(alert_group_responses.insert().values(group_id=ag.id, response_id=ra2.id))
        db.flush()

        # 验证分组侧的响应
        groups = ag_repo.with_responses()
        found = [g for g in groups if g.id == ag.id]
        assert len(found[0].responses) == 2

        # 验证响应侧的分组
        actions = ra_repo.with_groups()
        found_ra = [a for a in actions if a.id == ra1.id]
        assert len(found_ra[0].alert_groups) == 1
        assert found_ra[0].alert_groups[0].name == "紧急响应组"


class TestSituationEventIntegration:
    """事件记录完整链路集成测试。"""

    def test_event_from_view_exception(self, db):
        # 完整链路: Node → Video/Audio → View + AlertGroup → ExceptionDef → SituationEvent
        node = NodeRepo(db).create(token="full-chain")
        video = VideoDeviceRepo(db).create(name="chain-cam", node_id=node.id)
        audio = AudioDeviceRepo(db).create(name="chain-mic", node_id=node.id)
        view = MonitorViewRepo(db).create(video_id=video.id, audio_id=audio.id)
        ag = AlertGroupRepo(db).create(name="链路分组")
        exc = ExceptionDefRepo(db).create(name="事件测试异常", severity=SeverityLevel.CRITICAL, group_id=ag.id)

        event_repo = SituationEventRepo(db)
        event = event_repo.create(view_id=view.id, exception_id=exc.id)

        # 验证按视图和按时间范围查询
        from datetime import datetime, timedelta, timezone
        events_by_view = event_repo.by_view(view.id)
        assert len(events_by_view) == 1
        assert events_by_view[0].id == event.id

        now = datetime.now(timezone.utc)
        events_in_range = event_repo.by_time_range(
            start=now - timedelta(minutes=1),
            end=now + timedelta(minutes=1),
        )
        assert len(events_in_range) >= 1
