"""人脸识别——Part B 实现。

基于 YOLO person crop → dlib 人脸检测 → 128D 特征比对 NamedPerson 库。
产出 FaceRecognitionResult 枚举事件。
"""
"""Face recognition for the vision pipeline."""

from .face_recognizer import FaceRecognizer, FaceResult, FaceResultStatus

__all__ = ["FaceRecognizer", "FaceResult", "FaceResultStatus"]
