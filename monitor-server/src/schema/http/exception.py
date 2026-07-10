"""异常规则 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field

from src.constants import SeverityLevel


# ── 嵌套引用（避免循环导入，用简化结构）───────


class EnumTypeRef(BaseModel):
    """枚举类型简要引用。"""

    id: int
    name: str

    model_config = {"from_attributes": True}


class AlertGroupRef(BaseModel):
    """告警分组简要引用。"""

    id: int
    name: str

    model_config = {"from_attributes": True}


# ── ExceptionDef ────────────────────────────────


class ExceptionCreate(BaseModel):
    """创建异常规则请求体。"""

    name: str = Field(..., min_length=1, max_length=128, description="异常规则名称")
    severity: SeverityLevel = Field(..., description="严重级别")
    group_id: int = Field(..., description="告警分组 ID")
    face_result_id: int | None = Field(None, description="人脸识别结果条件 ID（可选）")
    fence_event_id: int | None = Field(None, description="电子围栏事件条件 ID（可选）")


class ExceptionUpdate(BaseModel):
    """更新异常规则请求体。"""

    name: str | None = Field(None, min_length=1, max_length=128, description="异常规则名称")
    severity: SeverityLevel | None = Field(None, description="严重级别")
    group_id: int | None = Field(None, description="告警分组 ID")
    face_result_id: int | None = Field(None, description="人脸识别结果条件 ID（可选）")
    fence_event_id: int | None = Field(None, description="电子围栏事件条件 ID（可选）")


class ExceptionResponse(BaseModel):
    """异常规则响应体（含所有关联）。"""

    id: int
    name: str
    severity: SeverityLevel
    group_id: int
    face_result_id: int | None = None
    fence_event_id: int | None = None
    created_at: datetime
    alert_group: AlertGroupRef | None = None
    entities: list[EnumTypeRef] = []
    actions: list[EnumTypeRef] = []
    sounds: list[EnumTypeRef] = []

    model_config = {"from_attributes": True}


# ── Binding ─────────────────────────────────────


class EntityBindRequest(BaseModel):
    entity_id: int = Field(..., description="实体类型 ID")


class ActionBindRequest(BaseModel):
    action_id: int = Field(..., description="行为类型 ID")


class SoundBindRequest(BaseModel):
    sound_id: int = Field(..., description="声音类型 ID")


class ExceptionListResponse(BaseModel):
    """异常规则分页列表响应体。"""

    items: list[ExceptionResponse]
    total: int
    page: int
    page_size: int
