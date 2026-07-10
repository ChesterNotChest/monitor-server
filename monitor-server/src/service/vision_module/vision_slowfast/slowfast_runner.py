"""SlowFast queueing and action event publishing."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

import numpy as np

from src.constants import SlowFastActionType
from src.service.vision_module.vision_event_bus import ACTION, event_bus

logger = logging.getLogger(__name__)

_CLIP_LENGTH = 32


class SlowFastState(Enum):
    IDLE = auto()
    ACTIVE = auto()
    ERROR = auto()


@dataclass
class ActionResult:
    track_id: int
    action_type_id: int
    label: str
    confidence: float
    source: str


InferenceFn = Callable[[list[np.ndarray]], ActionResult | None]


class SlowFastRunner:
    """Maintain per-track clip queues and publish ActionType events."""

    def __init__(
        self,
        *,
        clip_length: int = _CLIP_LENGTH,
        kinetics_infer: InferenceFn | None = None,
        ava_infer: InferenceFn | None = None,
    ) -> None:
        self.clip_length = clip_length
        self._queues: defaultdict[int, deque[np.ndarray]] = defaultdict(
            lambda: deque(maxlen=self.clip_length),
        )
        self._state = SlowFastState.IDLE
        self._kinetics_infer = kinetics_infer
        self._ava_infer = ava_infer
        self._models_loaded = False

    @property
    def state(self) -> SlowFastState:
        return self._state

    def load(self) -> bool:
        """Load optional SlowFast models once.

        The first implementation keeps model loading optional so queue behavior
        and pipeline integration can run without downloading heavyweight weights.
        """

        self._models_loaded = True
        return True

    def enqueue(self, track_id: int, frame_crop: np.ndarray) -> list[ActionResult]:
        queue = self._queues[track_id]
        queue.append(frame_crop.copy())
        self._state = SlowFastState.ACTIVE

        if len(queue) < self.clip_length:
            return []

        clip = list(queue)
        try:
            results = self._infer(track_id, clip)
        except Exception:
            logger.exception("SlowFast inference failed for track %s", track_id)
            queue.clear()
            self._state = SlowFastState.ERROR
            return []
        queue.clear()
        return results

    async def enqueue_and_publish(
        self,
        track_id: int,
        frame_crop: np.ndarray,
        view_id: int,
    ) -> list[ActionResult]:
        results = self.enqueue(track_id, frame_crop)
        if results:
            await event_bus.publish(
                ACTION,
                {
                    "view_id": view_id,
                    "actions": [
                        {
                            "track_id": result.track_id,
                            "action_type_id": result.action_type_id,
                            "label": result.label,
                            "confidence": result.confidence,
                            "source": result.source,
                        }
                        for result in results
                    ],
                },
            )
        return results

    def clear_track(self, track_id: int) -> None:
        self._queues.pop(track_id, None)
        if not self._queues:
            self._state = SlowFastState.IDLE

    def _infer(self, track_id: int, clip: list[np.ndarray]) -> list[ActionResult]:
        results: list[ActionResult] = []
        if self._kinetics_infer is not None:
            result = self._kinetics_infer(clip)
            if result is not None:
                result.track_id = track_id
                results.append(result)
        else:
            result = self.infer_kinetics(track_id, clip)
            if result is not None:
                results.append(result)

        if self._ava_infer is not None:
            result = self._ava_infer(clip)
            if result is not None:
                result.track_id = track_id
                results.append(result)
        else:
            results.extend(self.infer_ava(track_id, clip))
        return results

    def infer_kinetics(
        self,
        track_id: int,
        clip_32frames: list[np.ndarray],
    ) -> ActionResult | None:
        """Run Kinetics inference.

        Real model inference will be plugged in once weights are provisioned.
        Returning ``None`` keeps the queue/pipeline behavior deterministic.
        """

        return None

    def infer_ava(
        self,
        track_id: int,
        clip_32frames: list[np.ndarray],
    ) -> list[ActionResult]:
        """Run AVA per-box action inference."""

        return []


def make_action_result(
    track_id: int,
    action: SlowFastActionType,
    confidence: float,
    source: str = "mock",
) -> ActionResult:
    return ActionResult(
        track_id=track_id,
        action_type_id=int(action),
        label=action.name,
        confidence=confidence,
        source=source,
    )
