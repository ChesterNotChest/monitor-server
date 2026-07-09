"""异常定义管理 Schema。"""

from pydantic import BaseModel


class ExceptionCreate(BaseModel):
    name: str
    severity: int
    alert_group_id: int | None = None


class ExceptionResponse(BaseModel):
    id: int
    # 字段由 ExceptionDef 模型定义；简化版仅返回 id
    model_config = {"from_attributes": True}
