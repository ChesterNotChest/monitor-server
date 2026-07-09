"""用户 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """创建用户请求体。"""

    username: str = Field(..., min_length=1, max_length=64)
    role: int = Field(..., ge=1, le=4, description="1=安全员 2=管理员 3=负责人 4=运维员")


class UserResponse(BaseModel):
    """用户响应体。"""

    id: int
    username: str
    role: int
    created_at: datetime

    model_config = {"from_attributes": True}
