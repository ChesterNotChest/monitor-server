"""电子围栏 Schema。"""

from pydantic import BaseModel, Field


class FenceCreate(BaseModel):
    """创建电子围栏请求体。

    Swagger 示例: {"name":"禁区","view_id":1,"coords":[[100,100],[500,100],[500,400],[100,400]]}
    """

    name: str = Field(..., min_length=1, max_length=128, description="围栏名称")
    view_id: int = Field(..., description="关联监控视图 ID")
    coords: list[list[float]] = Field(
        ..., min_length=4, max_length=4,
        description="4 点不规则四边形 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]（像素坐标系）",
    )
    dwell_time: int = Field(10, ge=1, description="停留时限（秒）")
    density: float = Field(0.6, ge=0.0, le=1.0, description="密度阈值")
    leave_frames: int = Field(5, ge=1, description="离开判定帧数")
    safe_distance: int = Field(0, ge=0, description="安全距离（像素），0=禁用TOO_CLOSE")
    entry_delay_seconds: int = Field(0, ge=0, description="进入延迟（秒），0=立即触发，>0=停留X秒后触发")


class FenceResponse(BaseModel):
    id: int = Field(..., description="围栏 ID")
    name: str = Field(..., description="围栏名称")
    view_id: int = Field(..., description="关联监控视图 ID")
    coords: list[list[float]] = Field(..., description="4 点不规则四边形坐标（像素坐标系）")
    dwell_time: int = Field(..., description="停留时限（秒）")
    density: float = Field(..., description="密度阈值")
    leave_frames: int = Field(..., description="离开判定帧数")
    safe_distance: int = Field(..., description="安全距离（像素）")
    entry_delay_seconds: int = Field(..., description="进入延迟（秒）")

    model_config = {"from_attributes": True}
