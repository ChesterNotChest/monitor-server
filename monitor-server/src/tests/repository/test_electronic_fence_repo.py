"""ElectronicFenceRepo 冒烟测试。"""

import pytest
from src.repository.electronic_fence_repo import ElectronicFenceRepo
from src.models.node import Node
from src.models.video_device import VideoDevice
from src.models.audio_device import AudioDevice
from src.models.monitor_view import MonitorView


def _seed_view(db):
    """种子：Node → VideoDevice/AudioDevice → MonitorView。"""
    node = Node(token="fence-test")
    db.add(node)
    db.flush()
    video = VideoDevice(name="fence-cam", node_id=node.id)
    audio = AudioDevice(name="fence-mic", node_id=node.id)
    db.add_all([video, audio])
    db.flush()
    view = MonitorView(video_id=video.id, audio_id=audio.id)
    db.add(view)
    db.flush()
    return view


class TestElectronicFenceRepo:
    def test_create_and_get(self, db):
        view = _seed_view(db)
        repo = ElectronicFenceRepo(db)
        ef = repo.create(
            name="test-fence",
            view_id=view.id,
            coords=[[100, 200], [500, 200], [500, 400], [100, 400]],
        )
        assert ef.id is not None
        fetched = repo.get(ef.id)
        assert fetched.coords == [[100, 200], [500, 200], [500, 400], [100, 400]]

    def test_delete(self, db):
        view = _seed_view(db)
        repo = ElectronicFenceRepo(db)
        ef = repo.create(
            name="to-delete",
            view_id=view.id,
            coords=[[0, 0], [1, 0], [1, 1], [0, 1]],
        )
        assert repo.delete(ef.id) is True

    def test_count_and_paginate(self, db):
        view = _seed_view(db)
        repo = ElectronicFenceRepo(db)
        for i in range(3):
            repo.create(
                name=f"fence-{i}",
                view_id=view.id,
                coords=[[i, i], [i + 1, i], [i + 1, i + 1], [i, i + 1]],
            )
        assert repo.count() == 3
        items, total = repo.paginate(page=1, page_size=2)
        assert len(items) == 2
        assert total == 3
