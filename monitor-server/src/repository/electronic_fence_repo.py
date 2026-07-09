"""电子围栏 Repository。"""

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.electronic_fence import ElectronicFence


class ElectronicFenceRepo(BaseRepo[ElectronicFence]):
    """电子围栏数据访问层。"""

    model = ElectronicFence

    def __init__(self, db: Session) -> None:
        super().__init__(db)
