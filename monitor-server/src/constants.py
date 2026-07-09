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
    """YOLO 目标检测实体类别（整数枚举，数据库存整数值）。COCO 预训练 12 类。"""
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


class SlowFastActionType(enum.IntEnum):
    """SlowFast 行为识别类别（整数枚举，数据库存整数值）。Kinetics-400 预训练 12 类。"""
    WALKING = 1
    RUNNING = 2
    FALLING = 3
    FIGHTING = 4
    CLIMBING = 5
    THROWING = 6
    POINTING = 7
    WAVING = 8
    HUGGING = 9
    PUSHING = 10
    SITTING = 11
    STANDING = 12


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


class FaceRecognitionResult(enum.IntEnum):
    """人脸识别结果枚举。"""
    NO_RESULT = 1   # 画面中未检测到人脸
    STRANGER = 2    # 检测到人脸但不在录入人员库中
    NORMAL = 3      # 检测到人脸且匹配已录入人员


class FenceEventResult(enum.IntEnum):
    """电子围栏事件枚举。"""
    ENTERED = 1  # 闯入禁区


# ══════════════════════════════════════════════
# 用户与日志枚举
# ══════════════════════════════════════════════

class UserRole(enum.IntEnum):
    """用户角色枚举。"""
    SECURITY = 1   # 安全员
    ADMIN = 2      # 管理员
    MANAGER = 3    # 负责人
    OPERATOR = 4   # 运维员


class LogType(enum.IntEnum):
    """日志类型枚举。"""
    DEVICE = 1       # 设备状态变更
    OPERATION = 2    # 用户操作
    RECOGNITION = 3  # AI 识别结果
    ALERT = 4        # 告警处置
    SYSTEM = 5       # 系统事件
