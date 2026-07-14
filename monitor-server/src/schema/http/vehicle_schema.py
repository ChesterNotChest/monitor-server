"""Vehicle stats API schema."""

from pydantic import BaseModel


class VehicleStatsResponse(BaseModel):
    """View 车辆统计数据响应。"""

    view_id: int
    total_unique: dict[str, int]  # {"car": 15, "truck": 3, ...}
    current_frame: dict[str, int]  # 当前帧去重后
    fps: float
