"""FaceImage 存储服务测试。"""

import shutil
from io import BytesIO

import pytest
from starlette.datastructures import Headers

from src.config import settings
from src.service.named_person_module.face_image import (
    save_avatar,
    delete_avatar,
    _validate_avatar,
    _person_dir,
)


def _make_upload_file(content_type: str, filename: str, size: int, content: bytes = b"fake"):
    """辅助：构造模拟 UploadFile。"""
    headers = Headers({"content-type": content_type})
    # Use starlette UploadFile directly to control headers
    from starlette.datastructures import UploadFile
    return UploadFile(BytesIO(content), filename=filename, size=size, headers=headers)


class TestValidateAvatar:
    def test_accept_jpeg(self):
        f = _make_upload_file("image/jpeg", "face.jpg", 1024)
        _validate_avatar(f)  # no exception

    def test_accept_png(self):
        f = _make_upload_file("image/png", "face.png", 1024)
        _validate_avatar(f)  # no exception

    def test_reject_wrong_mime(self):
        f = _make_upload_file("text/plain", "face.txt", 1024)
        with pytest.raises(ValueError, match="仅支持 JPEG/PNG"):
            _validate_avatar(f)

    def test_reject_wrong_extension(self):
        f = _make_upload_file("image/jpeg", "face.gif", 1024)
        with pytest.raises(ValueError, match="仅支持 JPEG/PNG"):
            _validate_avatar(f)

    def test_reject_too_large(self):
        f = _make_upload_file("image/jpeg", "face.jpg", settings.MAX_AVATAR_SIZE + 1)
        with pytest.raises(ValueError, match="图片大小不能超过"):
            _validate_avatar(f)


class TestSaveAndDeleteAvatar:
    def test_save_avatar(self):
        person_id = 99901  # use high id to avoid collision
        f = _make_upload_file("image/jpeg", "face.jpg", 1024, b"test-image-data")
        try:
            relative = save_avatar(person_id, f)
            assert relative == f"person_{person_id}/avatar.jpg"
            assert _person_dir(person_id).exists()
        finally:
            shutil.rmtree(_person_dir(person_id), ignore_errors=True)

    def test_replace_avatar(self):
        person_id = 99902
        f1 = _make_upload_file("image/jpeg", "face.jpg", 1024, b"old-data")
        f2 = _make_upload_file("image/png", "face.png", 2048, b"new-data")
        try:
            save_avatar(person_id, f1)
            f2.file.seek(0)
            relative = save_avatar(person_id, f2)
            assert relative == f"person_{person_id}/avatar.png"
            assert not (_person_dir(person_id) / "avatar.jpg").exists()
            assert (_person_dir(person_id) / "avatar.png").exists()
        finally:
            shutil.rmtree(_person_dir(person_id), ignore_errors=True)

    def test_delete_avatar(self):
        person_id = 99903
        f = _make_upload_file("image/jpeg", "face.jpg", 1024, b"data")
        save_avatar(person_id, f)
        delete_avatar(person_id)
        assert not _person_dir(person_id).exists()

    def test_delete_avatar_idempotent(self):
        person_id = 99904
        assert not _person_dir(person_id).exists()
        delete_avatar(person_id)  # should not raise
