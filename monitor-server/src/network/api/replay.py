"""录制回放 REST API 路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.schema.http.replay import RecordingResponse
from src.service.replay_task import get_recordings
from src.repository.recording_repo import RecordingRepo

router = APIRouter(tags=["录制回放"])


@router.get(
    "/views/{id}/recordings",
    response_model=list[RecordingResponse],
)
def list_recordings(
    id: int,
    db: Session = Depends(get_db),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
):
    """查询指定视图的录制文件列表，可按时间范围筛选。"""
    items = get_recordings(db, view_id=id, start=start, end=end)
    return [RecordingResponse.model_validate(r) for r in items]


@router.get(
    "/recordings/{id}/stream",
    responses={
        404: {"description": "录制记录不存在或录制文件不存在"},
    },
)
def stream_recording(id: int, db: Session = Depends(get_db)):
    """流式传输录制文件（FLV 格式）。"""
    recording = RecordingRepo(db).get(id)
    if recording is None:
        raise HTTPException(status_code=404, detail="录制记录不存在")

    import os
    if not os.path.exists(recording.file_path):
        raise HTTPException(status_code=404, detail="录制文件不存在")

    return FileResponse(
        recording.file_path,
        media_type="video/x-flv",
        filename=recording.file_path.split("/")[-1],
    )
