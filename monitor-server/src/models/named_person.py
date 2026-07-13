"""命名人物模型 —— 关联人脸特征向量与头像。"""

from datetime import datetime

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import Base


class NamedPerson(Base):
    __tablename__ = "named_persons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    avatar_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    feat_json_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<NamedPerson {self.id}>"
