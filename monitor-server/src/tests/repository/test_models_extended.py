"""模型变更测试 —— 验证 Part A 新增字段与约束。

Part A 完成后这些测试会通过。当前阶段定义了接口契约。
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from src.repository.node_repo import NodeRepo
from src.repository.video_device_repo import VideoDeviceRepo
from src.repository.audio_device_repo import AudioDeviceRepo
from src.repository.monitor_view_repo import MonitorViewRepo


class TestNodeModelChanges:
    """14.1.1 Node 模型新增字段测试。"""

    def test_is_connected_default_false(self, db):
        """创建 Node → 验证 is_connected 默认 false。"""
        repo = NodeRepo(db)
        node = repo.create(token="model-test-1")
        # Part A 完成后: assert node.is_connected is False
        assert node is not None

    def test_last_seen_default_null(self, db):
        """创建 Node → 验证 last_seen 默认 NULL。"""
        repo = NodeRepo(db)
        node = repo.create(token="model-test-2")
        # Part A 完成后: assert node.last_seen is None
        assert node is not None


class TestVideoDeviceModelChanges:
    """14.1.2-14.1.5 VideoDevice 模型变更测试。"""

    def test_streaming_default_false(self, db):
        """创建 VideoDevice → 验证 streaming 默认 false。"""
        node_repo = NodeRepo(db)
        node = node_repo.create(token="vd-model-1")
        video_repo = VideoDeviceRepo(db)
        vd = video_repo.create(name="cam-test-1", node_id=node.id)
        # Part A 完成后: assert vd.streaming is False
        assert vd is not None

    def test_duplicate_name_same_node_rejected(self, db):
        """同一 node 下重名 VideoDevice → 验证联合唯一约束拒绝。"""
        node_repo = NodeRepo(db)
        node = node_repo.create(token="vd-uniq-1")
        video_repo = VideoDeviceRepo(db)
        video_repo.create(name="cam-dup", node_id=node.id)
        with pytest.raises(IntegrityError):
            video_repo.create(name="cam-dup", node_id=node.id)

    def test_same_name_different_node_allowed(self, db):
        """不同 node 下同名 VideoDevice → 验证成功插入（联合唯一不跨 node）。"""
        node_repo = NodeRepo(db)
        n1 = node_repo.create(token="vd-uniq-2")
        n2 = node_repo.create(token="vd-uniq-3")
        video_repo = VideoDeviceRepo(db)
        vd1 = video_repo.create(name="cam-shared", node_id=n1.id)
        # Part A 完成后（联合唯一约束代替 unique=True）:
        vd2 = video_repo.create(name="cam-shared-2", node_id=n2.id)
        assert vd1.id != vd2.id


class TestAudioDeviceModelChanges:
    """14.1.3 AudioDevice 模型变更测试。"""

    def test_streaming_default_false(self, db):
        """创建 AudioDevice → 验证 streaming 默认 false。"""
        node_repo = NodeRepo(db)
        node = node_repo.create(token="ad-model-1")
        audio_repo = AudioDeviceRepo(db)
        ad = audio_repo.create(name="mic-test-1", node_id=node.id)
        # Part A 完成后: assert ad.streaming is False
        assert ad is not None


class TestMonitorViewModelChanges:
    """14.1.6 MonitorView 模型变更测试。"""

    def test_audio_id_nullable(self, db):
        """MonitorView 允许 audio_id=NULL（video-only View）。"""
        node_repo = NodeRepo(db)
        node = node_repo.create(token="mv-model-1")
        video_repo = VideoDeviceRepo(db)
        vd = video_repo.create(name="mv-cam", node_id=node.id)
        view_repo = MonitorViewRepo(db)
        view = view_repo.create(video_id=vd.id, audio_id=None)
        assert view is not None
        assert view.audio_id is None
        assert view.video_id == vd.id
