"""引用计数逻辑测试 —— 验证 lifecycle.py 的推流启停判断。

Part A 完成后这些测试会通过。
"""

import pytest


class TestCheckAndStartStream:
    """14.5.1-14.5.2 check_and_start_stream 测试。"""

    def test_start_when_ref_count_zero(self, db):
        """check_and_start_stream 计数=0 → 调 send_command + update_streaming(True)，返回 True。"""
        # Part A 完成后:
        # from src.service.view_module.lifecycle import check_and_start_stream
        # 1. 创建设备，无 View 引用（ref_count=0）
        # 2. result = check_and_start_stream(db, "video", device_id)
        # 3. assert result is True
        # 4. 验证设备 streaming 变为 True
        pass

    def test_skip_when_ref_count_positive(self, db):
        """check_and_start_stream 计数>0 → 不调 send_command，返回 False。"""
        # Part A 完成后:
        # 1. 创建设备，创建一个 View 引用（ref_count>0）
        # 2. result = check_and_start_stream(db, "video", device_id)
        # 3. assert result is False
        # 4. 验证未调用 send_command
        pass


class TestCheckAndStopStream:
    """14.5.3-14.5.4 check_and_stop_stream 测试。"""

    def test_stop_when_ref_count_zero(self, db):
        """check_and_stop_stream 计数=0 → 调 send_command + update_streaming(False)，返回 True。"""
        # Part A 完成后:
        # from src.service.view_module.lifecycle import check_and_stop_stream
        # 1. 创建设备，删除所有 View（ref_count=0）
        # 2. result = check_and_stop_stream(db, "video", device_id)
        # 3. assert result is True
        # 4. 验证设备 streaming 变为 False
        pass

    def test_skip_when_ref_count_positive(self, db):
        """check_and_stop_stream 计数>0 → 不调 send_command，返回 False。"""
        # Part A 完成后:
        # 1. 创建设备，仍有 View 引用（ref_count>0）
        # 2. result = check_and_stop_stream(db, "video", device_id)
        # 3. assert result is False
        pass


class TestGetRefCount:
    """引用计数查询测试。"""

    def test_get_ref_count_video(self, db):
        """get_ref_count("video", video_id) → 返回正确计数。"""
        # Part A 完成后:
        # from src.service.view_module.lifecycle import get_ref_count
        # 创建 2 个 View 引用同一 video → count = 2
        pass

    def test_get_ref_count_audio(self, db):
        """get_ref_count("audio", audio_id) → 返回正确计数。"""
        # Part A 完成后:
        # 创建 1 个 View 引用 audio → count = 1
        pass

    def test_get_ref_count_unknown_type_raises(self):
        """get_ref_count("unknown", 1) → 抛出 ValueError。"""
        # Part A 完成后:
        # with pytest.raises(ValueError):
        #     get_ref_count(db, "unknown", 1)
        pass
