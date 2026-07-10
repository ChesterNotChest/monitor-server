"""检测枚举管理 Schema。"""

from datetime import datetime

from pydantic import BaseModel


class DetectionTypeCreate(BaseModel):
    name: str


class DetectionTypeResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
