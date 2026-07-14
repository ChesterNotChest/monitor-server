"""异常定义 API 路由 —— 负责人+运维员。"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.config import settings
from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.exception_schema import ExceptionCreate, ExceptionResponse
from src.service import exception_task

router = APIRouter(prefix="/exceptions", tags=["异常定义"])
_perm = Depends(require_permission("exception:manage"))


@router.get("/", response_model=list[ExceptionResponse])
def list_exceptions(db: Session = Depends(get_db), _user=_perm):
    """列出所有异常规则。

    **权限**: exception:manage
    """
    return exception_task.list_exceptions(db)


@router.post(
    "/",
    response_model=ExceptionResponse,
    status_code=201,
    responses={404: {"description": "关联的告警分组不存在"}},
)
def create_exception(body: ExceptionCreate, db: Session = Depends(get_db), _user=_perm):
    """创建异常规则。

    **权限**: exception:manage
    """
    try:
        return exception_task.create_exception(db, **body.model_dump(exclude_none=True))
    except IntegrityError as e:
        raise HTTPException(400, f"数据完整性错误: {e}")


# ── 录制全局设置（必须在 /{exc_id} 之前）──
from pydantic import BaseModel

class RecordingSettingsBody(BaseModel):
    max_seconds: int | None = None
    wind_down_seconds: int | None = None

_SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / "recording_settings.json"
if _SETTINGS_FILE.exists():
    try:
        saved = json.loads(_SETTINGS_FILE.read_text())
        settings.RECORDING_MAX_SECONDS = int(saved.get("max_seconds", settings.RECORDING_MAX_SECONDS))
        settings.RECORDING_WIND_DOWN_SECONDS = int(saved.get("wind_down_seconds", settings.RECORDING_WIND_DOWN_SECONDS))
    except Exception:
        pass

@router.get("/recording-settings/")
def get_recording_settings():
    return {"max_seconds": settings.RECORDING_MAX_SECONDS, "wind_down_seconds": settings.RECORDING_WIND_DOWN_SECONDS}

@router.put("/recording-settings/")
def put_recording_settings(body: RecordingSettingsBody, _user=_perm):
    new_max = body.max_seconds if body.max_seconds is not None else settings.RECORDING_MAX_SECONDS
    new_wd = body.wind_down_seconds if body.wind_down_seconds is not None else settings.RECORDING_WIND_DOWN_SECONDS
    settings.RECORDING_MAX_SECONDS = new_max
    settings.RECORDING_WIND_DOWN_SECONDS = new_wd
    try:
        _SETTINGS_FILE.write_text(json.dumps({"max_seconds": new_max, "wind_down_seconds": new_wd}))
    except Exception: pass
    return {"max_seconds": new_max, "wind_down_seconds": new_wd}

# ── 单个异常 CRUD ──

@router.put(
    "/{exc_id}/",
    response_model=ExceptionResponse,
    responses={404: {"description": "异常规则不存在"}},
)
def update_exception(exc_id: int, body: ExceptionCreate, db: Session = Depends(get_db), _user=_perm):
    """更新异常规则。

    **权限**: exception:manage
    """
    try:
        r = exception_task.update_exception(db, exc_id, **body.model_dump(exclude_none=True))
    except IntegrityError as e:
        raise HTTPException(400, f"数据完整性错误: {e}")
    if r is None: raise HTTPException(404)
    return r


@router.delete(
    "/{exc_id}/",
    status_code=204,
    responses={404: {"description": "异常规则不存在"}},
)
def delete_exception(exc_id: int, db: Session = Depends(get_db), _user=_perm):
    """删除异常规则。

    **权限**: exception:manage
    """
    try:
        if not exception_task.delete_exception(db, exc_id):
            raise HTTPException(404)
    except IntegrityError:
        raise HTTPException(400, "该异常已有告警事件关联，无法删除。请先处理相关告警事件")
