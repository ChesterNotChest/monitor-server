"""电子围栏模型。"""

from datetime import datetime

from sqlalchemy import Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import Base


class ElectronicFence(Base):
    __tablename__ = "electronic_fences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    coords: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ElectronicFence {self.id}>"
