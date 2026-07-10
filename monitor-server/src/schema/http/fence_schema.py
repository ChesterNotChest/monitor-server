"""电子围栏 Schema。"""

from pydantic import BaseModel, Field


class FenceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    view_id: int
    coords: list[list[float]] = Field(
        ..., min_length=4, max_length=4,
        description="4 点不规则四边形 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]（像素坐标系）",
    )
    dwell_time: int = Field(10, ge=1, description="停留时限（秒）")
    density: float = Field(0.6, ge=0.0, le=1.0, description="密度阈值")
    leave_frames: int = Field(5, ge=1, description="离开判定帧数")


class FenceResponse(BaseModel):
    id: int
    name: str
    view_id: int
    coords: list[list[float]]
    dwell_time: int
    density: float
    leave_frames: int

    model_config = {"from_attributes": True}
