"""泛型 Repository 基类 —— 封装通用 CRUD 操作。"""

from typing import Generic, TypeVar

from sqlalchemy import select, func
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepo(Generic[T]):
    """所有 Repository 的抽象基类。

    子类必须覆盖 ``model`` 类变量：:

        class FooRepo(BaseRepo[Foo]):
            model = Foo
    """

    model: type[T]

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── 查询 ──────────────────────────────────────

    def get(self, id: int) -> T | None:
        """按主键查询单条记录。"""
        return self.db.get(self.model, id)

    def all(self, *, offset: int = 0, limit: int = 100) -> list[T]:
        """全表查询，支持分页偏移。"""
        return list(
            self.db.scalars(
                select(self.model).offset(offset).limit(limit)
            )
        )

    def count(self) -> int:
        """返回表中总记录数。"""
        result = self.db.scalar(select(func.count()).select_from(self.model))
        return result or 0

    def exists(self, id: int) -> bool:
        """检查指定主键的记录是否存在。"""
        return self.get(id) is not None

    def paginate(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[T], int]:
        """分页查询，返回 ``(当前页数据, 总记录数)``。"""
        total = self.count()
        items = self.all(offset=(page - 1) * page_size, limit=page_size)
        return items, total

    # ── 写操作 ────────────────────────────────────

    def create(self, **kwargs: object) -> T:
        """创建一条新记录并 flush（不 commit）。"""
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, id: int) -> bool:
        """按主键删除记录。存在则删除并 flush，返回 True；否则返回 False。"""
        obj = self.get(id)
        if obj is None:
            return False
        self.db.delete(obj)
        self.db.flush()
        return True
