"""认证相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class UserResponse(BaseModel):
    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    role: str = Field(..., description="角色标识（security_guard / manager / operator）")
    is_active: bool = Field(..., description="账户是否启用")
    supervisor_id: int | None = Field(None, description="上级用户 ID")
    dingtalk_mobile: str | None = Field(None, description="钉钉绑定手机号")

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field("bearer", description="令牌类型（固定为 bearer）")
    user: UserResponse = Field(..., description="当前登录用户信息")
