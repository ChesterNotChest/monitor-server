"""告警引擎 —— 订阅 EventBus → 汇聚活跃事件 → 匹配 ExceptionDef → 创建 SituationEvent。

流程：
    1. 订阅 EventBus 全部 5 个 event type
    2. 内存活跃事件池 {event_type: [{payload, expires_at}, ...]}，TTL = ALERT_EVENT_TTL
    3. 每 ALERT_CHECK_INTERVAL 检查：清理过期 → 收集活跃 → 匹配 ExceptionDef → 触发
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.extensions import SessionLocal

# ── 事件类型常量（本地定义，避免 vision_module 的 numpy 依赖链） ──
ENTITY = "ENTITY"
ACTION = "ACTION"
SOUND = "SOUND"
FACE = "FACE"
FENCE = "FENCE"
RECORDING = "RECORDING"

# ── 可配置常量 ──
ALERT_EVENT_TTL: float = 5.0
ALERT_CHECK_INTERVAL: float = 5.0
ALERT_COOLDOWN: float = 30.0

logger = logging.getLogger(__name__)


@dataclass
class _EventEntry:
    payload: dict
    expires_at: float


class AlertEngine:
    """告警引擎 —— 单个 View 的告警规则匹配器。"""

    def __init__(self, view_id: int) -> None:
        self._view_id = view_id
        self._pool: dict[str, list[_EventEntry]] = {
            ENTITY: [], ACTION: [], SOUND: [], FACE: [], FENCE: [],
        }
        self._triggered: dict[tuple[int, int], float] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动告警引擎：订阅 EventBus，启动定时检查。"""
        from src.service.vision_module.vision_event_bus import event_bus

        self._running = True
        for event_type in self._pool:
            await event_bus.subscribe(event_type, self._on_event)
        self._task = asyncio.create_task(self._check_loop())
        logger.info("AlertEngine started for view %d", self._view_id)

    async def _on_event(self, payload: dict) -> None:
        now = time.time()
        event_type = payload.get("type", ENTITY)
        if event_type in self._pool:
            self._pool[event_type].append(_EventEntry(
                payload=payload,
                expires_at=now + ALERT_EVENT_TTL,
            ))

    async def _check_loop(self) -> None:
        while self._running:
            await asyncio.sleep(ALERT_CHECK_INTERVAL)
            try:
                await self._check()
            except Exception:
                logger.exception("AlertEngine check error view=%d", self._view_id)

    async def _check(self) -> None:
        now = time.time()

        # 1. 清理过期
        for et in self._pool:
            self._pool[et] = [e for e in self._pool[et] if e.expires_at > now]

        # 2. 收集活跃 ID
        active_entities = self._collect_ids(ENTITY, "entity_type_ids")
        active_actions = self._collect_ids(ACTION, "action_type_ids")
        active_sounds = self._collect_ids(SOUND, "sound_type_ids")
        active_faces = self._collect_ids(FACE, "face_result_ids")
        active_fences = self._collect_ids(FENCE, "fence_event_ids")

        if not any([active_entities, active_actions, active_sounds, active_faces, active_fences]):
            return

        # 3. 加载 ExceptionDef
        db = SessionLocal()
        try:
            from src.repository.exception_def_repo import ExceptionDefRepo
            repo = ExceptionDefRepo(db)
            exc_defs = repo.with_details() if hasattr(repo, "with_details") else repo.all()

            for exc in exc_defs:
                if self._match(exc, active_entities, active_actions, active_sounds,
                              active_faces, active_fences):
                    await self._trigger(db, exc, now)
        finally:
            db.close()

    def _match(self, exc, active_entities, active_actions, active_sounds,
               active_faces, active_fences) -> bool:
        """AND 条件匹配。

        def.entities ⊆ active_entities
        AND def.actions ⊆ active_actions
        AND def.sounds ⊆ active_sounds
        AND (def.face_result_id IS NULL OR def.face_result_id ∈ active_faces)
        AND (def.fence_event_id IS NULL OR def.fence_event_id ∈ active_fences)
        """
        if hasattr(exc, "entities") and exc.entities:
            if not set(e.id for e in exc.entities).issubset(active_entities):
                return False
        if hasattr(exc, "actions") and exc.actions:
            if not set(a.id for a in exc.actions).issubset(active_actions):
                return False
        if hasattr(exc, "sounds") and exc.sounds:
            if not set(s.id for s in exc.sounds).issubset(active_sounds):
                return False
        if exc.face_result_id is not None and exc.face_result_id not in active_faces:
            return False
        if exc.fence_event_id is not None and exc.fence_event_id not in active_fences:
            return False
        return True

    async def _trigger(self, db: Session, exc, now: float) -> None:
        dedup_key = (self._view_id, exc.id)

        if dedup_key in self._triggered:
            elapsed = now - self._triggered[dedup_key]
            if elapsed < ALERT_COOLDOWN:
                from src.service.vision_module.vision_event_bus import event_bus
                await event_bus.publish(RECORDING, {
                    "action": "keep_alive", "view_id": self._view_id,
                })
                return

        self._triggered[dedup_key] = now

        try:
            from src.repository.situation_event_repo import SituationEventRepo
            repo = SituationEventRepo(db)
            event = repo.create(view_id=self._view_id, exception_id=exc.id)
            logger.info(
                "Alert triggered: view=%d exception=%d severity=%s id=%d",
                self._view_id, exc.id, getattr(exc, "severity", None), event.id,
            )
        except Exception:
            logger.exception("Failed to create SituationEvent")

    def _collect_ids(self, event_type: str, key: str) -> set[int]:
        ids: set[int] = set()
        for entry in self._pool[event_type]:
            val = entry.payload.get(key, [])
            if isinstance(val, list):
                ids.update(val)
            elif isinstance(val, int):
                ids.add(val)
        return ids

    async def stop(self) -> None:
        """停止告警引擎。"""
        self._running = False
        from src.service.vision_module.vision_event_bus import event_bus
        for event_type in self._pool:
            await event_bus.unsubscribe(event_type, self._on_event)
        if self._task is not None:
            self._task.cancel()
        logger.info("AlertEngine stopped for view %d", self._view_id)
