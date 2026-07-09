"""人脸图片文件存储 —— 内部逻辑模块。

提供头像图片的本地磁盘存储、替换、删除及校验功能。
数据库仅存相对路径，文件实体存储在 ``FACE_IMAGE_DIR`` 下。
"""

import os
import shutil
from pathlib import Path

from fastapi import UploadFile

from src.config import settings

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
