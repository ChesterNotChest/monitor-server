"""MonitorViewRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.node_repo import NodeRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.repository.audio_device_repo import AudioDeviceRepo
from src.repository.monitor_view_repo import MonitorViewRepo


class TestMonitorViewRepo:
    @pytest.fixture
    def devices(self, db):
        node = NodeRepo(db).create(token="view-test-node")
        video = VideoDeviceRepo(db).create(name="view-cam", node_id=node.id)
        audio = AudioDeviceRepo(db).create(name="view-mic", node_id=node.id)
        return node, video, audio

    def test_create_full_view(self, db, devices):
        node, video, audio = devices
        repo = MonitorViewRepo(db)
        view = repo.create(video_id=video.id, audio_id=audio.id, cache_path="/tmp/cache")
        assert view.id is not None
        assert view.cache_path == "/tmp/cache"

    def test_create_video_only_view_accepted(self, db, devices):
        node, video, _ = devices
        repo = MonitorViewRepo(db)
        view = repo.create(video_id=video.id, audio_id=None)
        assert view is not None
        assert view.audio_id is None

    def test_device_in_use(self, db, devices):
        node, video, audio = devices
        repo = MonitorViewRepo(db)
        assert repo.device_in_use(video_id=video.id) is False
        assert repo.device_in_use(audio_id=audio.id) is False
        view = repo.create(video_id=video.id, audio_id=audio.id)
        assert repo.device_in_use(video_id=video.id) is True
        assert repo.device_in_use(audio_id=audio.id) is True

    def test_device_in_use_nonexistent_device(self, db):
        repo = MonitorViewRepo(db)
        assert repo.device_in_use(video_id=99999) is False

    def test_find_by_device(self, db, devices):
        node, video, audio = devices
        repo = MonitorViewRepo(db)
        audio2 = AudioDeviceRepo(db).create(name="view-mic-2", node_id=node.id)
        v1 = repo.create(video_id=video.id, audio_id=audio.id)
        v2 = repo.create(video_id=video.id, audio_id=audio2.id)
        views = repo.find_by_device(video_id=video.id)
        assert len(views) == 2
        views_audio = repo.find_by_device(audio_id=audio.id)
        assert len(views_audio) == 1

    def test_delete_view_releases_device(self, db, devices):
        node, video, audio = devices
        repo = MonitorViewRepo(db)
        view = repo.create(video_id=video.id, audio_id=audio.id)
        repo.delete(view.id)
        assert repo.device_in_use(video_id=video.id) is False
        assert repo.device_in_use(audio_id=audio.id) is False

    def test_delete_nonexistent(self, db):
        repo = MonitorViewRepo(db)
        assert repo.delete(99999) is False

    def test_fk_video_violation(self, db):
        repo = MonitorViewRepo(db)
        with pytest.raises(IntegrityError):
            repo.create(video_id=99999, audio_id=None)
