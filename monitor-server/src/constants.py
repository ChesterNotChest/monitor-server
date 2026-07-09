"""
全局常量定义。
"""

import enum


# ──────────────────────────────────────────────
# API 前缀
# ──────────────────────────────────────────────
API_PREFIX = "/api/v1"

# ──────────────────────────────────────────────
# 分页默认值
# ──────────────────────────────────────────────
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ══════════════════════════════════════════════
# 用户角色
# ══════════════════════════════════════════════

class Role(enum.StrEnum):
    """系统用户角色枚举。"""
    SECURITY_GUARD = "security_guard"
    MANAGER = "manager"
    OPERATOR = "operator"


# ══════════════════════════════════════════════
# AI 检测枚举
# ══════════════════════════════════════════════

class YOLOEntityType(enum.IntEnum):
    """YOLO 目标检测实体类别（整数枚举，数据库存整数值）。"""
    PERSON = 1
    CAR = 2
    TRUCK = 3
    BUS = 4
    MOTORCYCLE = 5
    BICYCLE = 6
    DOG = 7
    CAT = 8
    BIRD = 9
    BACKPACK = 10
    SUITCASE = 11
    KNIFE = 12
    GUN = 13
    FIRE = 14
    SMOKE = 15


class SlowFastActionType(enum.IntEnum):
    """SlowFast 行为识别类别（整数枚举，数据库存整数值）。"""
    WALKING = 1
    RUNNING = 2
    FALLING = 3
    FIGHTING = 4
    LOITERING = 5
    CROWDING = 6
    CLIMBING = 7
    THROWING = 8
    POINTING = 9
    WAVING = 10
    HUGGING = 11
    PUSHING = 12
    LYING_DOWN = 13
    SITTING = 14
    STANDING = 15


class YAMNetSoundType(enum.IntEnum):
    """YAMNet 音频分类声音类别（整数枚举，数据库存整数值）。"""
    GUNSHOT = 1
    SCREAM = 2
    SIREN = 3
    EXPLOSION = 4
    GLASS_BREAKING = 5
    DOG_BARKING = 6
    CAR_HORN = 7
    ENGINE = 8
    BABY_CRYING = 9
    ALARM = 10
    THUNDER = 11
    WIND = 12
    RAIN = 13
    FOOTSTEPS = 14
    SILENCE = 15


# ══════════════════════════════════════════════
# 异常与响应枚举
# ══════════════════════════════════════════════

class SeverityLevel(enum.IntEnum):
    """异常严重级别枚举。"""
    INFO = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4


class ResponseActionType(enum.IntEnum):
    """响应动作类型枚举。"""
    TRIGGER_RECORDING = 1
    SEND_NOTIFICATION = 2
    ACTIVATE_ALARM = 3
    CALL_API = 4
    SEND_EMAIL = 5
