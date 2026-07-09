"""检测枚举管理 Schema。"""

from pydantic import BaseModel


class DetectionTypeCreate(BaseModel):
    name: str


class DetectionTypeResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
