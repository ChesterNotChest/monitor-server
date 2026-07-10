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

    id: int = Field(..., description="人物 ID")
    name: str = Field(..., description="人物姓名")
    avatar_path: str | None = Field(None, description="头像文件路径")
    feat_json_id: str | None = Field(None, description="人脸特征标识（关联 AI 识别结果）")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class PersonListResponse(BaseModel):
    """命名人物分页列表响应体。"""

    items: list[PersonResponse] = Field(..., description="人物列表")
    total: int = Field(..., description="人物总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
