"""电子围栏 Schema。"""

from pydantic import BaseModel


class FenceCreate(BaseModel):
    coords: str  # JSON 格式坐标


class FenceResponse(BaseModel):
    id: int
    coords: str

    model_config = {"from_attributes": True}
