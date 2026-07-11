"""SlowFast 行为识别——Part B 实现。

ByteTrack per-person 32 帧 clip → Kinetics 场景分类 + AVA 人物动作。
产出 ActionType 枚举事件。
"""
"""SlowFast action inference queueing for the vision pipeline."""

from .slowfast_runner import ActionResult, SlowFastRunner, SlowFastState

__all__ = ["ActionResult", "SlowFastRunner", "SlowFastState"]
