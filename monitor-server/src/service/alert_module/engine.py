"""告警引擎 —— Pipeline 同步快照 → 匹配 → 立刻推送告警 + 启动录制。"""

from __future__ import annotations

import asyncio
import logging
import time

from src.extensions import SessionLocal

logger = logging.getLogger(__name__)

ALERT_CHECK_INTERVAL: float = 5.0
ALERT_COOLDOWN: float = 30.0


class AlertEngine:
    """告警引擎 —— 单个 View 的告警规则匹配器。

    不再订阅 EventBus 枚举信号。每帧由 Pipeline 通过 ActiveSignals
    全局快照（vision_annotation._ACTIVE_SIGNALS）馈送最新检测结果。
    """

    def __init__(self, view_id: int) -> None:
        self._view_id = view_id
        # 冷却 key: (view_id, exc_id) — 只看异常种类，不看触发对象
        self._triggered: dict[tuple[int, int], float] = {}
        self._ongoing: dict[tuple[int, int], dict] = {}
        self._last_emit: dict[tuple[int, int], str] = {}   # 节流: 上次输出的事件类型
        self._last_signals: frozenset | None = None          # 节流: 上次的 signals 快照
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动告警引擎：开始定时检查 loop（无需 EventBus 订阅）。"""
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info("AlertEngine started for view %d", self._view_id)

    async def _check_loop(self) -> None:
        while self._running:
            await asyncio.sleep(ALERT_CHECK_INTERVAL)
            try:
                await self._check()
            except Exception:
                logger.exception("AlertEngine check error view=%d", self._view_id)

    async def _check(self) -> None:
        now = time.time()

        # 1. 读取 Pipeline 最新快照
        import src.service.vision_module.vision_annotation as _van
        sig = _van._ACTIVE_SIGNALS
        if sig is None:
            self._end_inactive(set())
            return

        ae = set(sig.entity_type_ids)
        aa = set(sig.action_type_ids)
        as_ = set(sig.sound_type_ids)
        af = set(sig.face_result_ids)
        afe = set(sig.fence_result_ids)

        # 节流: 只在信号变化时输出
        _sig_key = frozenset({("E", frozenset(ae)), ("A", frozenset(aa)), ("S", frozenset(as_)), ("F", frozenset(af)), ("FE", frozenset(afe))})
        if _sig_key != self._last_signals:
            self._last_signals = _sig_key
            logger.info(
                "[AlertEngine v=%d] signals E=%s A=%s S=%s F=%s FE=%s",
                self._view_id, ae, aa, as_, af, afe,
            )

        if not any([ae, aa, as_, af, afe]):
            self._end_inactive(set())
            return

        # 2. 加载 ExceptionDef
        db = SessionLocal()
        try:
            from src.repository.exception_def_repo import ExceptionDefRepo
            excs = ExceptionDefRepo(db).with_details()
            matched_now: set[tuple[int, int]] = set()
            for exc in excs:
                if not self._match(exc, ae, aa, as_, af, afe):
                    continue
                key = (self._view_id, exc.id)
                matched_now.add(key)

                cd = getattr(exc, "cooldown_seconds", None) or ALERT_COOLDOWN
                if key in self._triggered:
                    elapsed = now - self._triggered[key]
                    if elapsed < cd:
                        # 录制已停止（MAX_DUR/wind_down）→ 强制 RESET，允许新录制
                        from src.service import replay_task
                        _sess = replay_task._sessions.get(self._view_id)
                        if key in self._ongoing and _sess and _sess.is_stopped():
                            self._ongoing.pop(key, None)
                            self._triggered.pop(key, None)
                            self._last_emit.pop(key, None)
                            matched_now.discard(key)
                            logger.info(
                                "[AlertEngine v=%d] MAX_DUR RESET key=(%d,%d)",
                                self._view_id, key[0], key[1],
                            )
                            continue

                        if key in self._ongoing:
                            self._keep_alive()
                        # 状态变化时才输出
                        if self._last_emit.get(key) != "cooldown":
                            self._last_emit[key] = "cooldown"
                            logger.info(
                                "[AlertEngine v=%d] cooldown HIT key=(%d,%d) elapsed=%.0fs remaining=%.0fs",
                                self._view_id, key[0], key[1], elapsed, cd - elapsed,
                            )
                        continue

                # cooldown 已过期 — 重置 timer
                self._triggered[key] = now

                if key not in self._ongoing:
                    # 真正的新触发
                    self._last_emit[key] = "trigger"
                    logger.info(
                        "[AlertEngine v=%d] TRIGGER key=(%d,%d) exc=%s",
                        self._view_id, key[0], key[1], getattr(exc, "name", "?"),
                    )
                    # 新告警 → 复用或新建录制 → 创建 SituationEvent → 推送
                    try:
                        from src.service import replay_task
                        # 检查是否有同 View 的活跃录制可复用
                        _existing_session = replay_task._sessions.get(self._view_id)
                        _active_rec = (
                            _existing_session.recording_id
                            if _existing_session and not _existing_session.is_stopped()
                            else None
                        )

                        from src.repository.situation_event_repo import SituationEventRepo
                        event = SituationEventRepo(db).create(
                            view_id=self._view_id, exception_id=exc.id,
                        )
                        db.commit()

                        mr = getattr(exc, "max_recording_seconds", 10) or 10
                        wd = getattr(exc, "wind_down_seconds", 10) or 10
                        if _active_rec:
                            rec_id = _active_rec
                            self._keep_alive()
                            logger.info(
                                "[AlertEngine v=%d] Alert: exc=%d id=%d rec=%s (REUSE)",
                                self._view_id, exc.id, event.id, rec_id,
                            )
                        else:
                            rec_id = self._start_rec({
                                "view_id": self._view_id,
                                "exception_id": exc.id,
                                "exception_name": getattr(exc, "name", None),
                                "severity": getattr(exc, "severity", None).name
                                if getattr(exc, "severity", None) else None,
                            }, mr, wd)
                            logger.info(
                                "[AlertEngine v=%d] Alert: exc=%d id=%d rec=%s (NEW)",
                                self._view_id, exc.id, event.id, rec_id,
                            )

                        # 回填 recording_id
                        if rec_id:
                            event.recording_id = rec_id
                            db.commit()

                        # WSS 推送
                        from src.network.wss.alert_handler import alert_registry
                        try:
                            await alert_registry.broadcast({
                                "id": event.id,
                                "view_id": event.view_id,
                                "exception_id": event.exception_id,
                                "exception_name": getattr(exc, "name", None),
                                "timestamp": event.timestamp.isoformat()
                                if event.timestamp else None,
                                "severity": getattr(exc, "severity", None).name
                                if getattr(exc, "severity", None) else None,
                                "recording_id": rec_id,
                            })
                        except Exception:
                            logger.exception("WSS broadcast failed")

                        self._ongoing[key] = {}
                    except Exception:
                        logger.exception("Failed to create alert")
                else:
                    # 检查录制是否已停止（MAX_DUR/wind_down）→ 重置状态允许新录制
                    from src.service import replay_task
                    _sess = replay_task._sessions.get(self._view_id)
                    if _sess and _sess.is_stopped():
                        if self._last_emit.get(key) != "maxdur_reset":
                            self._last_emit[key] = "maxdur_reset"
                            logger.info(
                                "[AlertEngine v=%d] MAX_DUR RESET key=(%d,%d)",
                                self._view_id, key[0], key[1],
                            )
                        self._ongoing.pop(key, None)
                        self._triggered.pop(key, None)
                        self._last_emit.pop(key, None)
                        matched_now.discard(key)
                    else:
                        self._keep_alive()
                        if self._last_emit.get(key) != "keepalive":
                            self._last_emit[key] = "keepalive"
                            logger.info(
                                "[AlertEngine v=%d] keep_alive key=(%d,%d)",
                                self._view_id, key[0], key[1],
                            )

            self._end_inactive(matched_now)
        finally:
            db.close()

    # ── 录制（直连 replay_task） ──

    def _start_rec(self, d: dict, mr: int, wd: int) -> int | None:
        from src.service import replay_task
        db2 = SessionLocal()
        try:
            return replay_task.alert_triggered(
                d["view_id"], db2, action="start",
                max_recording_seconds=mr, wind_down_seconds=wd,
                alert_details=d,
            )
        except Exception:
            logger.exception("start_rec failed")
            return None
        finally:
            db2.close()

    def _keep_alive(self):
        from src.service import replay_task
        db2 = SessionLocal()
        try:
            replay_task.alert_triggered(self._view_id, db2, action="keep_alive")
        except Exception:
            logger.exception("keep_alive failed")
        finally:
            db2.close()

    def _end_inactive(self, matched: set[tuple[int, int]]) -> None:
        ended = set(self._ongoing.keys()) - matched
        for key in ended:
            self._ongoing.pop(key)
            self._triggered.pop(key, None)
            self._last_emit.pop(key, None)
            logger.info(
                "[AlertEngine v=%d] END key=(%d,%d) cooldown RESET",
                self._view_id, key[0], key[1],
            )
            logger.info(
                "[AlertEngine v=%d] END key=(%d,%d) cooldown RESET",
                self._view_id, key[0], key[1],
            )
            from src.service import replay_task
            db2 = SessionLocal()
            try:
                replay_task.alert_triggered(key[0], db2, action="end")
            except Exception:
                logger.exception("end_rec failed")
            finally:
                db2.close()

    # ── 匹配 ──

    def _match(self, exc, ae, aa, as_, af, afe) -> bool:
        """AND 条件匹配。

        exc.entities ⊆ ae  AND  exc.actions ⊆ aa  AND  exc.sounds ⊆ as_
        AND (exc.face_result_id IS NULL OR exc.face_result_id ∈ af)
        AND (exc.fence_event_id IS NULL OR exc.fence_event_id ∈ afe)
        """
        if hasattr(exc, "entities") and exc.entities:
            if not set(e.id for e in exc.entities).issubset(ae):
                return False
        if hasattr(exc, "actions") and exc.actions:
            if not set(a.id for a in exc.actions).issubset(aa):
                return False
        if hasattr(exc, "sounds") and exc.sounds:
            if not set(s.id for s in exc.sounds).issubset(as_):
                return False
        if exc.face_result_id is not None and exc.face_result_id not in af:
            return False
        if exc.fence_event_id is not None and exc.fence_event_id not in afe:
            return False
        return True

    async def stop(self) -> None:
        """停止告警引擎。"""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("AlertEngine stopped for view %d", self._view_id)
