"""人脸图片文件存储 —— 内部逻辑模块。

提供头像图片的本地磁盘存储、替换、删除及校验功能，
以及从头像图片提取 128D 人脸特征编码。
数据库仅存相对路径，文件实体存储在 ``FACE_IMAGE_DIR`` 下。
"""

import json
import logging
import os
import shutil
from pathlib import Path

import numpy as np
from fastapi import UploadFile

from src.config import settings

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _validate_avatar(file: UploadFile) -> None:
    """校验上传文件的格式和大小，不合法时抛出 ValueError。"""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("仅支持 JPEG/PNG 格式")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("仅支持 JPEG/PNG 格式")

    if file.size and file.size > settings.MAX_AVATAR_SIZE:
        raise ValueError(f"图片大小不能超过 {settings.MAX_AVATAR_SIZE // (1024 * 1024)}MB")


def _person_dir(person_id: int) -> Path:
    """返回人物头像目录的绝对路径。"""
    return Path(settings.FACE_IMAGE_DIR).resolve() / f"person_{person_id}"


def save_avatar(person_id: int, file: UploadFile) -> str:
    """保存头像图片，返回相对路径（如 ``person_1/avatar.jpg``）。

    若已存在头像目录，先清空旧文件再写入新文件（处理扩展名变更）。
    """
    _validate_avatar(file)

    ext = os.path.splitext(file.filename or ".jpg")[1].lower()
    person_dir = _person_dir(person_id)

    # 清空旧文件（处理 jpg → png 切换）
    if person_dir.exists():
        shutil.rmtree(person_dir)

    person_dir.mkdir(parents=True, exist_ok=True)

    avatar_path = person_dir / f"avatar{ext}"
    content = file.file.read()
    avatar_path.write_bytes(content)

    return f"person_{person_id}/avatar{ext}"


def delete_avatar(person_id: int) -> None:
    """删除人物头像目录（幂等 —— 目录不存在则静默返回）。"""
    person_dir = _person_dir(person_id)
    if person_dir.exists():
        shutil.rmtree(person_dir)


def extract_face_encoding(person_id: int) -> str | None:
    """从已保存的头像图片提取 128D 人脸特征向量，返回 JSON 数组字符串。

    自动查找 person_{id}/ 目录下的 avatar.{jpg,jpeg,png}。
    若目录不存在、无头像文件、或未检测到人脸则返回 None。

    用于写入 NamedPerson.feat_json_id，使 FaceRecognizer 能在
    load_known_people() 时加载该人员的特征用于实时识别。
    """
    person_dir = _person_dir(person_id)
    if not person_dir.exists():
        return None

    avatar_file: Path | None = None
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = person_dir / f"avatar{ext}"
        if candidate.exists():
            avatar_file = candidate
            break
    if avatar_file is None:
        return None

    try:
        import face_recognition
    except Exception:
        logger.warning("face_recognition not installed; skip encoding for person %d", person_id)
        return None

    try:
        # 用管线同款路径：先找人脸位置 → crop → 再编码（避免全尺寸图直塞 dlib SIGSEGV）
        image = face_recognition.load_image_file(str(avatar_file))
        locations = face_recognition.face_locations(image)
        if not locations:
            logger.warning("No face found in avatar for person %d", person_id)
            return None

        top, right, bottom, left = locations[0]
        crop = np.ascontiguousarray(image[top:bottom, left:right])

        encoding = None
        try:
            encodings = face_recognition.face_encodings(crop,
                                                         known_face_locations=[(0, right - left, bottom - top, 0)])
            if encodings:
                encoding = encodings[0]
        except TypeError:
            # dlib ABI 不兼容时回退：不带 locations 参数
            logger.debug("dlib location-bound encoding failed, retrying without locations")
            encodings = face_recognition.face_encodings(crop)
            if encodings:
                encoding = encodings[0]

        if encoding is None:
            logger.warning("Face found but encoding failed for person %d", person_id)
            return None
        vector = np.asarray(encoding, dtype=float)
        return json.dumps(vector.tolist())
    except Exception:
        logger.exception("Failed to extract face encoding for person %d", person_id)
        return None
