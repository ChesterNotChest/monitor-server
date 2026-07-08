"""Repository 泛型基类 —— 封装通用 CRUD 操作。"""

from typing import TypeVar, Generic

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepo(Generic[T]):
    """泛型 Repository 基类。

    所有具体 Repository 必须继承此类并指定 `model` 类变量。
    仅执行 flush()，commit() 交由 Service 层统一控制。
    """

    model: type[T]

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── 查询 ─────────────────────────────────────

    def get(self, id: int) -> T | None:
        """按主键查询单条记录。"""
        return self.db.get(self.model, id)

    def all(self, *, offset: int = 0, limit: int = 100) -> list[T]:
        """全表查询，支持 offset/limit 分页。"""
        return (
            self.db.query(self.model)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        """返回表中记录总数。"""
        return self.db.query(self.model).count()

    def exists(self, id: int) -> bool:
        """检查指定主键的记录是否存在。"""
        return self.db.get(self.model, id) is not None

    def paginate(self, page: int = 1, page_size: int = 20) -> tuple[list[T], int]:
        """分页查询，返回 (当前页数据, 总记录数)。"""
        total = self.count()
        offset = (page - 1) * page_size
        items = self.all(offset=offset, limit=page_size)
        return items, total

    # ── 写入 ─────────────────────────────────────

    def create(self, **kwargs) -> T:
        """创建新记录并 flush（不 commit）。返回模型实例。"""
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.flush()
        return instance

    def delete(self, id: int) -> bool:
        """按主键删除记录并 flush（不 commit）。返回 True 表示删除成功。"""
        instance = self.db.get(self.model, id)
        if instance is None:
            return False
        self.db.delete(instance)
        self.db.flush()
        return True
