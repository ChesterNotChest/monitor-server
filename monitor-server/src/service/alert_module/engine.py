"""告警引擎 —— EventBus订阅 → 匹配 → 立刻推送告警 + 启动录制。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from src.extensions import SessionLocal
from src.service.vision_module.vision_event_bus import ENTITY, ACTION, SOUND, FACE, FENCE

logger = logging.getLogger(__name__)

ALERT_EVENT_TTL: float = 5.0
ALERT_CHECK_INTERVAL: float = 5.0
ALERT_COOLDOWN: float = 30.0


@dataclass
class _EventEntry:
    payload: dict
    expires_at: float


class AlertEngine:
    def __init__(self, view_id: int) -> None:
        self._view_id = view_id
        self._pool = {ENTITY: [], ACTION: [], SOUND: [], FACE: [], FENCE: []}
        self._triggered: dict[tuple[int, int, int], float] = {}
        self._ongoing: dict[tuple[int, int, int], dict] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        from src.service.vision_module.vision_event_bus import event_bus
        self._running = True
        for et in self._pool:
            await event_bus.subscribe(et, self._on_event)
        self._task = asyncio.create_task(self._check_loop())
        logger.info("AlertEngine started for view %d", self._view_id)

    async def _on_event(self, payload: dict) -> None:
        et = payload.get("type", ENTITY)
        if et in self._pool:
            self._pool[et].append(_EventEntry(payload=payload, expires_at=time.time() + ALERT_EVENT_TTL))

    async def _check_loop(self) -> None:
        while self._running:
            await asyncio.sleep(ALERT_CHECK_INTERVAL)
            try:
                await self._check()
            except Exception:
                logger.exception("AlertEngine check error view=%d", self._view_id)

    async def _check(self) -> None:
        now = time.time()
        for et in self._pool:
            self._pool[et] = [e for e in self._pool[et] if e.expires_at > now]

        ae = self._cids(ENTITY, "entity_type_ids")
        aa = self._cids(ACTION, "action_type_ids")
        as_ = self._cids(SOUND, "sound_type_ids")
        af = self._cids(FACE, "face_result_ids")
        afe = self._cids(FENCE, "fence_event_ids")

        if not any([ae, aa, as_, af, afe]):
            self._end_inactive(set())
            return

        db = SessionLocal()
        try:
            from src.repository.exception_def_repo import ExceptionDefRepo
            excs = ExceptionDefRepo(db).with_details()
            matched_now: set[tuple[int, int, int]] = set()
            for exc in excs:
                if not self._match(exc, ae, aa, as_, af, afe):
                    continue
                tid = self._ft(ENTITY, ae) or self._ft(FACE, af) or -1
                key = (self._view_id, exc.id, tid)
                matched_now.add(key)

                cd = getattr(exc, "cooldown_seconds", None) or ALERT_COOLDOWN
                if key in self._triggered and now - self._triggered[key] < cd:
                    self._triggered[key] = now
                    if key in self._ongoing:
                        self._keep_alive()
                    continue

                self._triggered[key] = now

                if key not in self._ongoing:
                    # 新告警 → 创建 SituationEvent + 启动录制 → 推送告警(含recording_id)
                    try:
                        from src.repository.situation_event_repo import SituationEventRepo
                        event = SituationEventRepo(db).create(view_id=self._view_id, exception_id=exc.id)
                        db.commit()  # 先提交释放写锁，否则 _start_rec 的 SQLite 写会被阻塞

                        # 启动录制（立即创建Recording行，返回recording_id）
                        mr = getattr(exc, "max_recording_seconds", 10) or 10
                        wd = getattr(exc, "wind_down_seconds", 10) or 10
                        rec_id = self._start_rec({
                            "view_id": self._view_id, "exception_id": exc.id,
                            "exception_name": getattr(exc, "name", None),
                            "track_id": tid,
                            "severity": getattr(exc, "severity", None).name if getattr(exc, "severity", None) else None,
                        }, mr, wd)

                        # 回填 recording_id
                        if rec_id:
                            event.recording_id = rec_id
                            db.commit()
                        logger.info("Alert: view=%d exc=%d id=%d track=%d rec=%s", self._view_id, exc.id, event.id, tid, rec_id)

                        # 写入 Web 日志中心（不影响告警主流程）
                        try:
                            from src.service import log_task
                            log_task.record_alert_event(
                                db, event=event, exception_def=exc, recording_id=rec_id
                            )
                            db.commit()
                        except Exception:
                            db.rollback()
                            logger.exception("Failed to record alert log")

                        # WSS 推送（recording_id 已就绪，前端立即可回放）
                        from src.network.wss.alert_handler import alert_registry
                        try:
                            await alert_registry.broadcast({
                                "id": event.id, "view_id": event.view_id,
                                "exception_id": event.exception_id,
                                "exception_name": getattr(exc, "name", None),
                                "track_id": tid,
                                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                                "severity": getattr(exc, "severity", None).name if getattr(exc, "severity", None) else None,
                                "recording_id": rec_id,
                            })
                        except Exception:
                            logger.exception("WSS broadcast failed")

                        self._ongoing[key] = {}
                    except Exception:
                        logger.exception("Failed to create alert")
                else:
                    self._keep_alive()

            self._end_inactive(matched_now)
        finally:
            db.close()

    # ── 录制（直连 replay_task） ──

    def _start_rec(self, d: dict, mr: int, wd: int) -> int | None:
        from src.service import replay_task
        db2 = SessionLocal()
        try:
            return replay_task.alert_triggered(d["view_id"], db2, action="start",
                                               max_recording_seconds=mr, wind_down_seconds=wd,
                                               alert_details=d)
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

    def _end_inactive(self, matched):
        ended = set(self._ongoing.keys()) - matched
        for key in ended:
            self._ongoing.pop(key)
            # 录制停止 → 重置冷却，下次可立即重新触发
            self._triggered.pop(key, None)
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
        if hasattr(exc, "entities") and exc.entities:
            if not set(e.id for e in exc.entities).issubset(ae): return False
        if hasattr(exc, "actions") and exc.actions:
            if not set(a.id for a in exc.actions).issubset(aa): return False
        if hasattr(exc, "sounds") and exc.sounds:
            if not set(s.id for s in exc.sounds).issubset(as_): return False
        if exc.face_result_id is not None and exc.face_result_id not in af: return False
        if exc.fence_event_id is not None and exc.fence_event_id not in afe: return False
        return True

    def _cids(self, et, key):
        ids = set()
        for e in self._pool[et]:
            v = e.payload.get(key, [])
            if isinstance(v, list): ids.update(v)
            elif isinstance(v, int): ids.add(v)
        return ids

    def _ft(self, et, active):
        for e in self._pool[et]:
            for x in e.payload.get("entities", []):
                if isinstance(x, dict) and x.get("entity_type_id") in active:
                    return x.get("track_id")
            if e.payload.get("track_id"): return int(e.payload["track_id"])
        return None

    async def stop(self) -> None:
        self._running = False
        from src.service.vision_module.vision_event_bus import event_bus
        for et in self._pool:
            await event_bus.unsubscribe(et, self._on_event)
        if self._task: self._task.cancel()
