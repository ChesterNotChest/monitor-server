"""命名人物 HTTP Schema —— Pydantic 请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class PersonCreate(BaseModel):
    """创建命名人物请求体。"""

    name: str = Field(..., min_length=1, max_length=128, description="人物姓名")


class PersonUpdate(BaseModel):
    """更新命名人物请求体。"""

    name: str | None = Field(None, min_length=1, max_length=128, description="人物姓名（可选）")


class PersonResponse(BaseModel):
    """命名人物响应体。"""

    id: int
    name: str
    avatar_path: str | None
    feat_json_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PersonListResponse(BaseModel):
    """命名人物分页列表响应体。"""

    items: list[PersonResponse]
    total: int
    page: int
    page_size: int
