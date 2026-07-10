"""告警分级管理 Schema。"""

from datetime import datetime

from pydantic import BaseModel


class ResponseActionRef(BaseModel):
    """响应动作简要引用。"""
    id: int
    name: str

    model_config = {"from_attributes": True}


class AlertGroupCreate(BaseModel):
    name: str


class AlertGroupResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    responses: list[ResponseActionRef] = []

    model_config = {"from_attributes": True}
