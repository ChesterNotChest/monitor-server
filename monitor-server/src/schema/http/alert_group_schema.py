"""告警分级管理 Schema。"""

from pydantic import BaseModel


class AlertGroupCreate(BaseModel):
    name: str


class AlertGroupResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
