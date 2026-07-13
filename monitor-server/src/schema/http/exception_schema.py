"""异常定义辅助 Schema —— exception_router 使用的精简版。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ExceptionCreate(BaseModel):
    """创建异常规则请求体（精简版）。"""

    name: str = Field(..., min_length=1, max_length=128, description="异常规则名称")
    severity: int = Field(..., ge=1, le=4, description="严重级别：1=INFO 2=WARNING 3=CRITICAL 4=EMERGENCY")
    group_id: int | None = Field(None, description="告警分组 ID")
    entity_ids: list[int] = Field(default_factory=list, description="实体类型 ID 列表（多选，AND 关系）")
    action_ids: list[int] = Field(default_factory=list, description="行为类型 ID 列表（多选，AND 关系）")
    sound_ids: list[int] = Field(default_factory=list, description="声音类型 ID 列表（多选，AND 关系）")
    face_result_id: int | None = Field(None, description="人脸识别结果条件 ID（可选）")
    fence_event_id: int | None = Field(None, description="电子围栏事件条件 ID（可选）")
    cooldown_seconds: int = Field(30, ge=0, description="告警冷却时间（秒），0 表示使用全局默认")
    max_recording_seconds: int = Field(10, ge=0, description="录制时间上限（秒），默认10")
    wind_down_seconds: int = Field(10, ge=0, description="空闲等待时间（秒），同一框+类型无新检测后等待X秒结束录制，默认10")


class ExceptionResponse(BaseModel):
    """异常规则响应体（精简版，仅返回数字 ID，不返回嵌套对象）。"""

    id: int = Field(..., description="异常规则 ID")
    name: str = Field(..., description="异常规则名称")
    severity: int = Field(..., ge=1, le=4, description="严重级别：1=INFO 2=WARNING 3=CRITICAL 4=EMERGENCY")
    group_id: int | None = Field(None, description="告警分组 ID")
    entity_ids: list[int] = Field(default_factory=list, description="实体类型条件 ID 列表")
    action_ids: list[int] = Field(default_factory=list, description="行为类型条件 ID 列表")
    sound_ids: list[int] = Field(default_factory=list, description="声音类型条件 ID 列表")
    face_result_id: int | None = Field(None, description="人脸识别结果条件 ID（可选）")
    fence_event_id: int | None = Field(None, description="电子围栏事件条件 ID（可选）")
    cooldown_seconds: int = Field(30, description="告警冷却时间（秒）")
    max_recording_seconds: int = Field(10, description="录制时间上限（秒）")
    wind_down_seconds: int = Field(10, description="空闲等待时间（秒）")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}
