"""临时冒烟测试 —— 验证 Group A Repository 的 CRUD 操作。
运行方式: python -m src.repository._smoke_test
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.extensions import SessionLocal, Base, engine
from src.repository import (
    NodeRepo, VideoDeviceRepo, AudioDeviceRepo, MonitorViewRepo,
    ElectronicFenceRepo, EntityTypeRepo, ActionTypeRepo, SoundTypeRepo,
)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    # ── NodeRepo ────────────────────────
    node_repo = NodeRepo(db)
    node = node_repo.create(token='test-token-001')
    assert node_repo.by_token('test-token-001') is not None
    assert node_repo.get(node.id) is not None
    assert node_repo.count() == 1
    assert node_repo.exists(node.id) is True
    assert len(node_repo.all(limit=5)) == 1
    items, total = node_repo.paginate(page=1, page_size=10)
    assert len(items) == 1 and total == 1

    # ── VideoDeviceRepo ─────────────────
    video_repo = VideoDeviceRepo(db)
    vd = video_repo.create(name='camera-01', node_id=node.id)
    assert len(video_repo.by_node(node.id)) == 1

    # ── AudioDeviceRepo ─────────────────
    audio_repo = AudioDeviceRepo(db)
    ad = audio_repo.create(name='mic-01', node_id=node.id)
    assert len(audio_repo.by_node(node.id)) == 1

    # ── MonitorViewRepo ─────────────────
    view_repo = MonitorViewRepo(db)
    mv = view_repo.create(video_id=vd.id, audio_id=ad.id, cache_path='/tmp/view1')
    assert view_repo.device_in_use(video_id=vd.id) is True
    assert view_repo.device_in_use(video_id=99999) is False
    assert len(view_repo.find_by_device(video_id=vd.id)) == 1

    # ── Enum Repos ──────────────────────
    assert ElectronicFenceRepo(db).count() == 0
    assert EntityTypeRepo(db).count() == 0
    assert ActionTypeRepo(db).count() == 0
    assert SoundTypeRepo(db).count() == 0

    # ── delete ──────────────────────────
    assert view_repo.delete(mv.id) is True
    assert audio_repo.delete(ad.id) is True
    assert video_repo.delete(vd.id) is True
    assert node_repo.delete(node.id) is True

    # ── edge cases ──────────────────────
    assert node_repo.delete(99999) is False
    assert node_repo.get(99999) is None
    assert node_repo.exists(99999) is False

    print('\n=== All CRUD tests passed! ===')

finally:
    db.rollback()
    db.close()
