"""异常定义辅助 Schema —— exception_router 使用的精简版。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ExceptionCreate(BaseModel):
    """创建异常规则请求体。

    示例（刀具检测）:
      {"name":"刀具检测","severity":3,"group_id":1,"entity_ids":[12],"cooldown_seconds":30,"max_recording_seconds":10,"wind_down_seconds":10}

    示例（陌生人+打架）:
      {"name":"陌生人打架","severity":4,"group_id":1,"entity_ids":[1],"action_ids":[4],"face_result_id":2}
    """

    name: str = Field(..., min_length=1, max_length=128, description="异常规则名称")
    severity: int = Field(..., ge=1, le=4, description="严重级别：1=INFO 2=WARNING 3=CRITICAL 4=EMERGENCY")
    group_id: int | None = Field(None, description="告警分组 ID（必填，关联 alert_groups 表）")
    entity_ids: list[int] = Field(default_factory=list, description="实体类型 ID 列表。满足其中一个即匹配（OR）。例: [1]=Person, [12]=Knife")
    action_ids: list[int] = Field(default_factory=list, description="行为类型 ID 列表。满足其中一个即匹配（OR）。例: [4]=Fighting, [13]=Smoking")
    sound_ids: list[int] = Field(default_factory=list, description="声音类型 ID 列表。满足其中一个即匹配（OR）。例: [1]=Gunshot, [2]=Scream")
    face_result_id: int | None = Field(None, description="人脸识别结果条件 ID。2=Stranger。设置后仅陌生人触发")
    fence_event_id: int | None = Field(None, description="电子围栏事件条件 ID。1=ENTERED。设置后仅闯入围栏时触发")
    cooldown_seconds: int = Field(30, ge=0, description="冷却时间（秒）。同 View 同规则触发后 X 秒内不再重复。0=无冷却")
    max_recording_seconds: int = Field(10, ge=0, description="录制时间上限（秒）。单次录制最长 X 秒，到时间自动停。0=不限")
    wind_down_seconds: int = Field(10, ge=0, description="空闲等待（秒）。最后一条告警消失后等待 X 秒再停录")


class ExceptionResponse(BaseModel):
    """异常规则响应体。

    返回示例:
      {"id":1,"name":"人员出现","severity":2,"group_id":1,"entity_ids":[1],
       "action_ids":[],"sound_ids":[],"face_result_id":null,"fence_event_id":null,
       "cooldown_seconds":30,"max_recording_seconds":10,"wind_down_seconds":10,"created_at":"..."}
    """

    id: int = Field(..., description="异常规则 ID")
    name: str = Field(..., description="异常规则名称")
    severity: int = Field(..., ge=1, le=4, description="严重级别：1=INFO 2=WARNING 3=CRITICAL 4=EMERGENCY")
    group_id: int | None = Field(None, description="告警分组 ID")
    entity_ids: list[int] = Field(default_factory=list, description="匹配的实体类型 ID 列表（OR 关系）")
    action_ids: list[int] = Field(default_factory=list, description="匹配的行为类型 ID 列表（OR 关系）")
    sound_ids: list[int] = Field(default_factory=list, description="匹配的声音类型 ID 列表（OR 关系）")
    face_result_id: int | None = Field(None, description="人脸识别结果条件 ID")
    fence_event_id: int | None = Field(None, description="电子围栏事件条件 ID")
    cooldown_seconds: int = Field(30, description="冷却时间（秒）")
    max_recording_seconds: int = Field(10, description="录制时间上限（秒）")
    wind_down_seconds: int = Field(10, description="空闲等待（秒）")
    created_at: datetime = Field(..., description="创建时间 (ISO 8601)")

    model_config = {"from_attributes": True}
