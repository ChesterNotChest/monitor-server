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
                        self._triggered[key] = now
                        if key in self._ongoing:
                            self._keep_alive()
                        logger.info(
                            "[AlertEngine v=%d] cooldown HIT key=(%d,%d) elapsed=%.0fs remaining=%.0fs",
                            self._view_id, key[0], key[1], elapsed, cd - elapsed,
                        )
                        continue

                self._triggered[key] = now
                logger.info(
                    "[AlertEngine v=%d] TRIGGER key=(%d,%d) exc=%s",
                    self._view_id, key[0], key[1], getattr(exc, "name", "?"),
                )

                if key not in self._ongoing:
                    # 新告警 → 创建 SituationEvent + 启动录制 → 推送告警(含recording_id)
                    try:
                        from src.repository.situation_event_repo import SituationEventRepo
                        event = SituationEventRepo(db).create(
                            view_id=self._view_id, exception_id=exc.id,
                        )
                        db.commit()

                        # 启动录制（立即创建Recording行，返回recording_id）
                        mr = getattr(exc, "max_recording_seconds", 10) or 10
                        wd = getattr(exc, "wind_down_seconds", 10) or 10
                        rec_id = self._start_rec({
                            "view_id": self._view_id,
                            "exception_id": exc.id,
                            "exception_name": getattr(exc, "name", None),
                            "severity": getattr(exc, "severity", None).name
                            if getattr(exc, "severity", None) else None,
                        }, mr, wd)

                        # 回填 recording_id
                        if rec_id:
                            event.recording_id = rec_id
                            db.commit()
                        logger.info(
                            "[AlertEngine v=%d] Alert: exc=%d id=%d rec=%s",
                            self._view_id, exc.id, event.id, rec_id,
                        )

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
                    self._keep_alive()
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
            # 录制停止 → 重置冷却，下次可立即重新触发
            self._triggered.pop(key, None)
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
