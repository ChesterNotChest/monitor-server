"""通用 HTTP 响应模型。"""

from pydantic import BaseModel, Field


class OkResponse(BaseModel):
    """通用操作成功响应。"""

    ok: bool = Field(True, description="操作是否成功")


class DeleteResponse(BaseModel):
    """删除操作成功响应。"""

    ok: bool = Field(True, description="删除是否成功")


class StatusResponse(BaseModel):
    """通用状态响应。"""

    status: str = Field(..., description="状态描述", examples=["ok", "error"])
