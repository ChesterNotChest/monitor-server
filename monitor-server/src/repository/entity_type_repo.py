"""实体类型（YOLO）Repository。"""

from sqlalchemy.orm import Session

from .base import BaseRepo
from ..models.entity_type import EntityType


class EntityTypeRepo(BaseRepo[EntityType]):
    """YOLO 实体类型枚举数据访问层。"""

    model = EntityType

    def __init__(self, db: Session) -> None:
        super().__init__(db)
