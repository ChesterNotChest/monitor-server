"""人脸识别结果枚举 Repository。"""

from .base import BaseRepo
from ..models.face_recognition_result import FaceRecognitionResult


class FaceRecognitionResultRepo(BaseRepo[FaceRecognitionResult]):
    model = FaceRecognitionResult
