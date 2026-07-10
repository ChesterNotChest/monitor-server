"""用户 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """创建用户请求体。"""

    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    role: int = Field(..., ge=1, le=4, description="角色编号：1=安全员 2=管理员 3=负责人 4=运维员")


class UserResponse(BaseModel):
    """用户响应体（用于用户管理 CRUD，与 auth 中的 UserResponse 字段不同）。"""

    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    role: int = Field(..., description="角色编号：1=安全员 2=管理员 3=负责人 4=运维员")
    created_at: datetime = Field(..., description="用户创建时间")

    model_config = {"from_attributes": True}
