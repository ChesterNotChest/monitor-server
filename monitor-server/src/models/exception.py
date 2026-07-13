"""异常枚举模型 + 与 AI 检测结果的多对多关联表。"""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Enum, DateTime, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import Base
from ..constants import SeverityLevel


# ── 多对多关联表 ──────────────────────────────

exception_entities = Table(
    "exception_entities",
    Base.metadata,
    Column("exception_id", Integer, ForeignKey("exceptions.id", ondelete="CASCADE"), primary_key=True),
    Column("entity_id", Integer, ForeignKey("entity_types.id", ondelete="CASCADE"), primary_key=True),
)

exception_actions = Table(
    "exception_actions",
    Base.metadata,
    Column("exception_id", Integer, ForeignKey("exceptions.id", ondelete="CASCADE"), primary_key=True),
    Column("action_id", Integer, ForeignKey("action_types.id", ondelete="CASCADE"), primary_key=True),
)

exception_sounds = Table(
    "exception_sounds",
    Base.metadata,
    Column("exception_id", Integer, ForeignKey("exceptions.id", ondelete="CASCADE"), primary_key=True),
    Column("sound_id", Integer, ForeignKey("sound_types.id", ondelete="CASCADE"), primary_key=True),
)


# ── Exception 模型 ────────────────────────────

class ExceptionDef(Base):
    """异常定义 —— 组合 AI 检测结果构成异常规则。"""

    __tablename__ = "exceptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel), nullable=False,
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("alert_groups.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    face_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("face_recognition_results.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    fence_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("fence_event_types.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    cooldown_seconds: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False, server_default="30",
    )
    max_recording_seconds: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False, server_default="10",
    )
    wind_down_seconds: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False, server_default="10",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 关联
    alert_group: Mapped["AlertGroup"] = relationship("AlertGroup")
    face_recognition_result: Mapped["FaceRecognitionResult | None"] = relationship("FaceRecognitionResult")
    fence_event_type: Mapped["FenceEventType | None"] = relationship("FenceEventType")
    entities: Mapped[list["EntityType"]] = relationship(
        "EntityType", secondary=exception_entities, lazy="selectin"
    )
    actions: Mapped[list["ActionType"]] = relationship(
        "ActionType", secondary=exception_actions, lazy="selectin"
    )
    sounds: Mapped[list["SoundType"]] = relationship(
        "SoundType", secondary=exception_sounds, lazy="selectin"
    )

    @property
    def entity_ids(self) -> list[int]:
        return [e.id for e in self.entities] if self.entities else []

    @property
    def action_ids(self) -> list[int]:
        return [a.id for a in self.actions] if self.actions else []

    @property
    def sound_ids(self) -> list[int]:
        return [s.id for s in self.sounds] if self.sounds else []

    def __repr__(self) -> str:
        return f"<ExceptionDef {self.id} severity={self.severity.name}>"
