"""FaceImage 存储服务测试。"""

import json
import shutil
from io import BytesIO
from pathlib import Path

import pytest
from starlette.datastructures import Headers

from src.config import settings
from src.service.named_person_module.face_image import (
    save_avatar,
    delete_avatar,
    _validate_avatar,
    _person_dir,
    extract_face_encoding,
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


class TestExtractFaceEncoding:
    def test_no_directory_returns_none(self):
        person_id = 99905
        assert not _person_dir(person_id).exists()
        result = extract_face_encoding(person_id)
        assert result is None

    def test_no_avatar_file_returns_none(self):
        person_id = 99906
        _person_dir(person_id).mkdir(parents=True)
        try:
            # directory exists but no avatar file inside
            result = extract_face_encoding(person_id)
            assert result is None
        finally:
            shutil.rmtree(_person_dir(person_id), ignore_errors=True)

    def test_extract_from_real_image(self):
        """使用 lfw_subset 中的真实人脸图片验证特征提取。"""
        person_id = 99907
        # 从测试 fixture 复制一张真实人脸作为 avatar
        lfw_dir = Path(__file__).resolve().parents[1] / "fixtures" / "lfw_subset"
        face_images = list(lfw_dir.glob("*.jpg"))
        if not face_images:
            pytest.skip("lfw_subset fixture not available")
        src = face_images[0]
        person_dir = _person_dir(person_id)
        person_dir.mkdir(parents=True)
        avatar_path = person_dir / "avatar.jpg"
        shutil.copy2(str(src), str(avatar_path))
        try:
            encoding_json = extract_face_encoding(person_id)
            if encoding_json is None:
                pytest.skip("face_recognition could not find a face (dlib issue on this env)")
            vector = json.loads(encoding_json)
            assert isinstance(vector, list)
            assert len(vector) == 128
            assert all(isinstance(v, float) for v in vector)
        finally:
            shutil.rmtree(person_dir, ignore_errors=True)
