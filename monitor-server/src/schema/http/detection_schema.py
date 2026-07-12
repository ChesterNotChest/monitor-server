"""检测枚举管理 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class DetectionTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="枚举名称")


class DetectionTypeResponse(BaseModel):
    id: int = Field(..., description="枚举 ID")
    name: str = Field(..., description="枚举名称")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}
