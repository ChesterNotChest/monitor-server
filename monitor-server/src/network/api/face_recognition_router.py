"""人脸识别结果枚举查询 API 路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.repository.face_recognition_result_repo import FaceRecognitionResultRepo
from src.schema.http.detection_schema import DetectionTypeResponse

router = APIRouter(prefix="/face-recognition-results", tags=["人脸识别结果"])


@router.get("", response_model=list[DetectionTypeResponse])
def list_results(db: Session = Depends(get_db)):
    """列出所有人脸识别结果枚举（NO_RESULT / STRANGER / NORMAL）。"""
    return FaceRecognitionResultRepo(db).all()
