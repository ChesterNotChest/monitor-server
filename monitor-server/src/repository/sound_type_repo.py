"""声音类型（YAMNet）Repository。"""

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.sound_type import SoundType


class SoundTypeRepo(BaseRepo[SoundType]):
    """YAMNet 声音类型枚举数据访问层。"""

    model = SoundType

    def __init__(self, db: Session) -> None:
        super().__init__(db)
