"""录制回放 REST API 路由。"""

import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.schema.http.replay import RecordingResponse
from src.service.replay_task import get_recordings
from src.repository.recording_repo import RecordingRepo

router = APIRouter(tags=["录制回放"])

MIME_MAP = {".flv": "video/x-flv", ".mp4": "video/mp4", ".mkv": "video/x-matroska", ".webm": "video/webm", ".avi": "video/x-msvideo"}


@router.get("/views/{id}/recordings/", response_model=list[RecordingResponse])
def list_recordings(id: int, db: Session = Depends(get_db), start: datetime | None = Query(None), end: datetime | None = Query(None)):
    items = get_recordings(db, view_id=id, start=start, end=end)
    return [RecordingResponse.model_validate(r) for r in items]


@router.get("/recordings/{id}/stream/")
def stream_recording(id: int, db: Session = Depends(get_db)):
    recording = RecordingRepo(db).get(id)
    if recording is None:
        raise HTTPException(status_code=404, detail="录制记录不存在")
    if not os.path.exists(recording.file_path):
        raise HTTPException(status_code=404, detail="录制文件不存在")
    ext = os.path.splitext(recording.file_path)[1].lower()
    return FileResponse(
        recording.file_path,
        media_type=MIME_MAP.get(ext, "application/octet-stream"),
        filename=os.path.basename(recording.file_path),
    )
