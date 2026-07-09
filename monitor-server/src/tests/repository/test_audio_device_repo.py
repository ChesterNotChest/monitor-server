"""AudioDeviceRepo 冒烟测试。"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.repository.node_repo import NodeRepo
from src.repository.audio_device_repo import AudioDeviceRepo


class TestAudioDeviceRepo:
    @pytest.fixture
    def node(self, db):
        return NodeRepo(db).create(token="audio-test-node")

    def test_create_and_get(self, db, node):
        repo = AudioDeviceRepo(db)
        ad = repo.create(name="mic-01", node_id=node.id)
        assert ad.id is not None
        assert repo.get(ad.id).name == "mic-01"

    def test_by_node(self, db, node):
        repo = AudioDeviceRepo(db)
        repo.create(name="mic-a", node_id=node.id)
        repo.create(name="mic-b", node_id=node.id)
        assert len(repo.by_node(node.id)) == 2

    def test_delete(self, db, node):
        repo = AudioDeviceRepo(db)
        ad = repo.create(name="mic-del", node_id=node.id)
        assert repo.delete(ad.id) is True

    def test_unique_name_violation(self, db, node):
        repo = AudioDeviceRepo(db)
        repo.create(name="mic-dup", node_id=node.id)
        with pytest.raises(IntegrityError):
            repo.create(name="mic-dup", node_id=node.id)

    def test_fk_node_violation(self, db):
        repo = AudioDeviceRepo(db)
        with pytest.raises(IntegrityError):
            repo.create(name="orphan-mic", node_id=99999)
