"""命名人物 Repository。"""

from sqlalchemy import select

from src.models.named_person import NamedPerson
from .base import BaseRepo


class NamedPersonRepo(BaseRepo[NamedPerson]):
    model = NamedPerson

    def find_by_name(self, name: str) -> NamedPerson | None:
        """按姓名查询单条记录，用于唯一性校验。"""
        return self.db.scalar(select(NamedPerson).where(NamedPerson.name == name))
