"""异常规则 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field

from src.constants import SeverityLevel


# ── 嵌套引用（避免循环导入，用简化结构）───────


class EnumTypeRef(BaseModel):
    """枚举类型简要引用。"""

    id: int = Field(..., description="枚举类型 ID")
    name: str = Field(..., description="枚举类型名称")

    model_config = {"from_attributes": True}


class AlertGroupRef(BaseModel):
    """告警分组简要引用。"""

    id: int = Field(..., description="告警分组 ID")
    name: str = Field(..., description="告警分组名称")

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

    id: int = Field(..., description="异常规则 ID")
    name: str = Field(..., description="异常规则名称")
    severity: SeverityLevel = Field(..., description="严重级别（1=INFO 2=WARNING 3=CRITICAL 4=EMERGENCY）")
    group_id: int = Field(..., description="告警分组 ID")
    face_result_id: int | None = Field(None, description="人脸识别结果条件 ID（可选）")
    fence_event_id: int | None = Field(None, description="电子围栏事件条件 ID（可选）")
    created_at: datetime = Field(..., description="创建时间")
    alert_group: AlertGroupRef | None = Field(None, description="关联的告警分组信息")
    entities: list[EnumTypeRef] = Field(default_factory=list, description="关联的实体类型列表")
    actions: list[EnumTypeRef] = Field(default_factory=list, description="关联的行为类型列表")
    sounds: list[EnumTypeRef] = Field(default_factory=list, description="关联的声音类型列表")

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
