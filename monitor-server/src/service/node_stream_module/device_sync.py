"""设备同步 —— 当 Node 上报设备变更时同步到数据库。

Part A 完成后需引入 ``VideoDeviceRepo.upsert`` 和 ``AudioDeviceRepo.upsert``。
"""

from sqlalchemy.orm import Session


def sync_devices(
    db: Session,
    node_id: int,
    videos: list[dict],
    audios: list[dict],
) -> None:
    """遍历视频/音频列表，已存在的跳过（基于 (node_id, name) 联合唯一），不存在的插入 DB。

    当前阶段此函数保留备用 —— 连接握手时 Server 直接查询已有设备返回，不经过 sync；
    后续 DEVICE_CHANGED 事件实现时会用到。
    """
    from src.repository.video_device_repo import VideoDeviceRepo
    from src.repository.audio_device_repo import AudioDeviceRepo

    video_repo = VideoDeviceRepo(db)
    audio_repo = AudioDeviceRepo(db)

    for v in videos:
        video_repo.upsert(node_id, v["name"])

    for a in audios:
        audio_repo.upsert(node_id, a["name"])
