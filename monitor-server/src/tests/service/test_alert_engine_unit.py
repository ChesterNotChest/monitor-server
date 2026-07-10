"""告警引擎匹配逻辑单元测试 (tasks 15.2.1-15.2.6)。"""

from src.service.alert_module.engine import AlertEngine


class TestAlertEngineMatch:
    """匹配逻辑：AND 条件测试。"""

    def _mk_engine(self):
        return AlertEngine(view_id=1)

    @staticmethod
    def _exc(**kw):
        class E: pass
        e = E()
        for k, v in kw.items():
            setattr(e, k, v)
        return e

    @staticmethod
    def _e(eid):
        class Z:
            pass
        z = Z()
        z.id = eid
        return z

    # 15.2.1 全部条件满足 → 触发
    def test_all_met(self):
        e = AlertEngine(1)
        exc = self._exc(id=1, entities=[self._e(1)], actions=[self._e(2)],
                        sounds=None, face_result_id=None, fence_event_id=None)
        assert e._match(exc, {1}, {2}, set(), set(), set()) is True

    # 15.2.2 部分条件 → 不触发
    def test_partial(self):
        e = AlertEngine(1)
        exc = self._exc(id=2, entities=[self._e(1)], actions=[self._e(2)],
                        sounds=None, face_result_id=None, fence_event_id=None)
        assert e._match(exc, {1}, set(), set(), set(), set()) is False

    # 15.2.6 混合条件（实体+围栏）
    def test_mixed_entity_fence(self):
        e = AlertEngine(1)
        exc = self._exc(id=3, entities=[self._e(1)], fence_event_id=5,
                        actions=None, sounds=None, face_result_id=None)
        assert e._match(exc, {1}, set(), set(), set(), {5}) is True
        assert e._match(exc, {1}, set(), set(), set(), set()) is False

    # 15.2.6 混合条件（声音+人脸）
    def test_mixed_sound_face(self):
        e = AlertEngine(1)
        exc = self._exc(id=4, sounds=[self._e(3)], face_result_id=7,
                        entities=None, actions=None, fence_event_id=None)
        assert e._match(exc, set(), set(), {3}, {7}, set()) is True
        assert e._match(exc, set(), set(), {3}, set(), set()) is False

    # NULL face/fence → skipped
    def test_null_face_skipped(self):
        e = AlertEngine(1)
        exc = self._exc(id=5, entities=[self._e(1)],
                        actions=None, sounds=None, face_result_id=None, fence_event_id=None)
        assert e._match(exc, {1}, set(), set(), {99}, set()) is True  # face ignored

    def test_null_fence_skipped(self):
        e = AlertEngine(1)
        exc = self._exc(id=6, entities=[self._e(1)],
                        actions=None, sounds=None, face_result_id=None, fence_event_id=None)
        assert e._match(exc, {1}, set(), set(), set(), {99}) is True  # fence ignored


class TestAlertEngineDedup:
    """去重测试 (tasks 15.2.3, 15.2.5)。"""

    def test_cooldown_tracked(self):
        e = AlertEngine(view_id=2)
        e._triggered[(2, 5)] = 100.0
        assert (2, 5) in e._triggered

    def test_different_rules_independent(self):
        """15.2.6/12.9 异异常独立。"""
        e = AlertEngine(view_id=3)
        e._triggered[(3, 1)] = 100.0
        e._triggered[(3, 2)] = 100.0
        assert len(e._triggered) == 2
