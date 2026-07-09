"""VideoDeviceRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.node_repo import NodeRepo
from src.repository.video_device_repo import VideoDeviceRepo


class TestVideoDeviceRepo:
    @pytest.fixture
    def node(self, db):
        return NodeRepo(db).create(token="video-test-node")

    def test_create_and_get(self, db, node):
        repo = VideoDeviceRepo(db)
        vd = repo.create(name="cam-01", node_id=node.id)
        assert vd.id is not None
        assert repo.get(vd.id).name == "cam-01"

    def test_by_node(self, db, node):
        repo = VideoDeviceRepo(db)
        repo.create(name="cam-a", node_id=node.id)
        repo.create(name="cam-b", node_id=node.id)
        devices = repo.by_node(node.id)
        assert len(devices) == 2

    def test_by_node_empty(self, db, node):
        repo = VideoDeviceRepo(db)
        assert len(repo.by_node(node.id)) == 0

    def test_delete(self, db, node):
        repo = VideoDeviceRepo(db)
        vd = repo.create(name="cam-del", node_id=node.id)
        assert repo.delete(vd.id) is True
        assert repo.get(vd.id) is None

    def test_unique_name_violation(self, db, node):
        repo = VideoDeviceRepo(db)
        repo.create(name="cam-dup", node_id=node.id)
        with pytest.raises(IntegrityError):
            repo.create(name="cam-dup", node_id=node.id)

    def test_fk_node_violation(self, db):
        repo = VideoDeviceRepo(db)
        with pytest.raises(IntegrityError):
            repo.create(name="orphan-cam", node_id=99999)
