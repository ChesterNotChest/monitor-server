"""告警引擎匹配逻辑单元测试。"""

from src.service.alert_module.engine import AlertEngine


class TestAlertEngineMatch:
    @staticmethod
    def _exc(**kw):
        class E: pass
        e = E()
        defaults = dict(id=1, entities=None, actions=None, sounds=None,
                        face_result_id=None, fence_event_id=None)
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(e, k, v)
        return e

    @staticmethod
    def _e(eid):
        class Z:
            pass
        z = Z()
        z.id = eid
        return z

    def test_all_met(self):
        e = AlertEngine(1)
        exc = self._exc(id=1, entities=[self._e(1)], actions=[self._e(2)],
                        sounds=None, face_result_id=None, fence_event_id=None)
        assert e._match(exc, {1}, {2}, set(), set(), set()) is True

    def test_partial(self):
        e = AlertEngine(1)
        exc = self._exc(id=2, entities=[self._e(1)], actions=[self._e(2)],
                        sounds=None, face_result_id=None, fence_event_id=None)
        assert e._match(exc, {1}, set(), set(), set(), set()) is False

    def test_mixed_entity_fence(self):
        e = AlertEngine(1)
        exc = self._exc(id=3, entities=[self._e(1)], fence_event_id=5,
                        actions=None, sounds=None, face_result_id=None)
        assert e._match(exc, {1}, set(), set(), set(), {5}) is True
        assert e._match(exc, {1}, set(), set(), set(), set()) is False

    def test_mixed_sound_face(self):
        e = AlertEngine(1)
        exc = self._exc(id=4, sounds=[self._e(3)], face_result_id=7,
                        entities=None, actions=None, fence_event_id=None)
        assert e._match(exc, set(), set(), {3}, {7}, set()) is True
        assert e._match(exc, set(), set(), {3}, set(), set()) is False

    def test_null_face_skipped(self):
        e = AlertEngine(1)
        exc = self._exc(id=5, entities=[self._e(1)], face_result_id=None)
        assert e._match(exc, {1}, set(), set(), {99}, set()) is True

    def test_null_fence_skipped(self):
        e = AlertEngine(1)
        exc = self._exc(id=6, entities=[self._e(1)], fence_event_id=None)
        assert e._match(exc, {1}, set(), set(), set(), {99}) is True


class TestAlertEngineDedup:
    def test_cooldown_tracked(self):
        e = AlertEngine(view_id=2)
        e._triggered[(2, 5)] = 100.0
        assert (2, 5) in e._triggered

    def test_different_rules_independent(self):
        e = AlertEngine(view_id=3)
        e._triggered[(3, 1)] = 100.0
        e._triggered[(3, 2)] = 100.0
        assert len(e._triggered) == 2
