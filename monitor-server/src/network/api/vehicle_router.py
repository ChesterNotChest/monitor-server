"""Vehicle stats REST API — 查询指定 View 的车辆统计数据。"""

from fastapi import APIRouter, Depends

from src.extensions import get_db
from src.schema.http.vehicle_schema import VehicleStatsResponse

router = APIRouter(prefix="/views", tags=["vehicle-stats"])


@router.get("/{view_id}/vehicle-stats/", response_model=VehicleStatsResponse)
async def get_vehicle_stats(view_id: int, db=Depends(get_db)):
    """查询指定 View 的车辆累计统计与当前帧快照。

    统计数据为管线内存态——View 管线活跃时返回累计值，未活跃时返回全零。
    """
    # 验证 View 是否存在
    from src.repository.monitor_view_repo import MonitorViewRepo
    repo = MonitorViewRepo(db)
    view = repo.get(view_id)
    if view is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="View not found")

    from src.service.vision_task import _vehicle_processors
    processor = _vehicle_processors.get(view_id)

    if processor is None:
        # 管线未启动，返回全零
        return VehicleStatsResponse(
            view_id=view_id,
            total_unique={"car": 0, "truck": 0, "bus": 0, "motorcycle": 0, "bicycle": 0},
            current_frame={"car": 0, "truck": 0, "bus": 0, "motorcycle": 0, "bicycle": 0},
            fps=0.0,
        )

    stats = processor.get_stats()
    return VehicleStatsResponse(
        view_id=view_id,
        total_unique=stats.total_unique,
        current_frame=stats.current_frame,
        fps=stats.fps,
    )
