"""告警分级管理 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ResponseActionRef(BaseModel):
    """响应动作简要引用。"""
    id: int = Field(..., description="响应动作 ID")
    name: str = Field(..., description="响应动作名称")

    model_config = {"from_attributes": True}


class AlertGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="告警分组名称")


class AlertGroupResponse(BaseModel):
    id: int = Field(..., description="告警分组 ID")
    name: str = Field(..., description="分组名称")
    created_at: datetime = Field(..., description="创建时间")
    responses: list[ResponseActionRef] = Field(default_factory=list, description="关联的响应动作列表")

    model_config = {"from_attributes": True}
