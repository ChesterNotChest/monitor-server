"""Dashboard API 路由 —— 所有角色可访问。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.dashboard_schema import DashboardStats, DashboardTrends
from src.service import dashboard_task

router = APIRouter(prefix="/dashboard", tags=["仪表板"])


@router.get("/stats/", response_model=DashboardStats)
def stats(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("dashboard:view")),
):
    """整体态势统计。

    **权限**: dashboard:view
    """
    return dashboard_task.get_stats(db)


@router.get("/trends/", response_model=DashboardTrends)
def trends(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("dashboard:view")),
):
    """告警趋势数据。

    **权限**: dashboard:view
    """
    return dashboard_task.get_trends(db)
