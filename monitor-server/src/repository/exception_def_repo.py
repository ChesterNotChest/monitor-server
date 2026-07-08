"""异常定义 Repository。"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.exception import ExceptionDef
from src.constants import SeverityLevel
from .base import BaseRepo


class ExceptionDefRepo(BaseRepo[ExceptionDef]):
    model = ExceptionDef

    def by_severity(self, severity: SeverityLevel) -> list[ExceptionDef]:
        """按严重级别过滤异常定义。"""
        return list(
            self.db.scalars(
                select(ExceptionDef).where(ExceptionDef.severity == severity)
            )
        )

    def by_group(self, group_id: int) -> list[ExceptionDef]:
        """按告警分组过滤异常定义。"""
        return list(
            self.db.scalars(
                select(ExceptionDef).where(ExceptionDef.group_id == group_id)
            )
        )

    def with_details(self) -> list[ExceptionDef]:
        """查询所有异常定义，eager load 全部关联。"""
        return list(
            self.db.scalars(
                select(ExceptionDef)
                .options(
                    selectinload(ExceptionDef.alert_group),
                    selectinload(ExceptionDef.entities),
                    selectinload(ExceptionDef.actions),
                    selectinload(ExceptionDef.sounds),
                )
            )
        )
