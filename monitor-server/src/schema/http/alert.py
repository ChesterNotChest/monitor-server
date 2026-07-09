"""告警分组与响应动作 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


# ── ResponseAction ──────────────────────────────


class ResponseActionCreate(BaseModel):
    """创建响应动作请求体。"""

    name: str = Field(..., min_length=1, max_length=64, description="响应动作名称（如 trigger_recording）")


class ResponseActionUpdate(BaseModel):
    """更新响应动作请求体。"""

    name: str = Field(..., min_length=1, max_length=64, description="响应动作名称")


class ResponseActionResponse(BaseModel):
    """响应动作响应体。"""

    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AlertGroup ──────────────────────────────────


class AlertGroupCreate(BaseModel):
    """创建告警分组请求体。"""

    name: str = Field(..., min_length=1, max_length=64, description="分组名称（如 高优先级）")


class AlertGroupUpdate(BaseModel):
    """更新告警分组请求体。"""

    name: str = Field(..., min_length=1, max_length=64, description="分组名称")


class AlertGroupResponse(BaseModel):
    """告警分组响应体（含已绑定的响应动作列表）。"""

    id: int
    name: str
    created_at: datetime
    responses: list[ResponseActionResponse] = []

    model_config = {"from_attributes": True}


# ── Binding ─────────────────────────────────────


class ResponseBindRequest(BaseModel):
    """绑定响应动作请求体。"""

    response_id: int = Field(..., description="响应动作 ID")
