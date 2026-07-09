"""枚举类型通用 Schema —— EntityType / ActionType / SoundType / ResponseAction 共用。"""

from datetime import datetime

from pydantic import BaseModel, Field


class EnumTypeCreate(BaseModel):
    """创建枚举类型请求体。"""

    name: str = Field(..., min_length=1, max_length=64, description="枚举名称")


class EnumTypeUpdate(BaseModel):
    """更新枚举类型请求体。"""

    name: str = Field(..., min_length=1, max_length=64, description="枚举名称")


class EnumTypeResponse(BaseModel):
    """枚举类型响应体。"""

    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
