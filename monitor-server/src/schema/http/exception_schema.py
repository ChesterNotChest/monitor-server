"""异常定义辅助 Schema —— exception_router 使用的精简版。

详细的 CRUD Schema（含嵌套关联对象）参见 src/schema/http/exception.py。
本文件为精简版本，API 仅返回数字 ID，不返回嵌套对象。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ExceptionCreate(BaseModel):
    """创建异常规则请求体（精简版）。"""

    name: str = Field(..., min_length=1, max_length=128, description="异常规则名称")
    severity: int = Field(..., ge=1, le=4, description="严重级别：1=INFO 2=WARNING 3=CRITICAL 4=EMERGENCY")
    group_id: int | None = Field(None, description="告警分组 ID")
    face_result_id: int | None = Field(None, description="人脸识别结果条件 ID（可选）")
    fence_event_id: int | None = Field(None, description="电子围栏事件条件 ID（可选）")


class ExceptionResponse(BaseModel):
    """异常规则响应体（精简版，仅返回数字 ID，不返回嵌套对象）。"""

    id: int = Field(..., description="异常规则 ID")
    name: str = Field(..., description="异常规则名称")
    severity: int = Field(..., description="严重级别：1=INFO 2=WARNING 3=CRITICAL 4=EMERGENCY")
    group_id: int | None = Field(None, description="告警分组 ID")
    face_result_id: int | None = Field(None, description="人脸识别结果条件 ID（可选）")
    fence_event_id: int | None = Field(None, description="电子围栏事件条件 ID（可选）")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}
