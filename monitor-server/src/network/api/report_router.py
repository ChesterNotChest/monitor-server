"""报表 API 路由 —— 负责人专有。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.report_schema import ReportResponse
from src.service import report_task

router = APIRouter(prefix="/reports", tags=["报表"])
_perm = Depends(require_permission("report:view"))


@router.get("/weekly", response_model=ReportResponse)
def weekly_report(db: Session = Depends(get_db), _user=_perm):
    return report_task.get_weekly_report(db)


@router.get("/monthly", response_model=ReportResponse)
def monthly_report(db: Session = Depends(get_db), _user=_perm):
    return report_task.get_monthly_report(db)
