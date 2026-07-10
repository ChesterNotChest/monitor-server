"""异常定义辅助 Schema。

详细的 CRUD Schema 参见 src/schema/http/exception.py。
本文件为精简版本，供内部引用使用。
"""

from pydantic import BaseModel


class ExceptionCreate(BaseModel):
    """创建异常规则请求体（精简版，完整版见 exception.py）。"""
    name: str
    severity: int
    group_id: int | None = None
    face_result_id: int | None = None
    fence_event_id: int | None = None


class ExceptionResponse(BaseModel):
    """异常规则响应体（精简版，完整版见 exception.py）。"""
    id: int
    name: str
    severity: int
    face_result_id: int | None = None
    fence_event_id: int | None = None

    model_config = {"from_attributes": True}
