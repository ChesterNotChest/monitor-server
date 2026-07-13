"""认证 REST API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.schema.http.auth_schema import LoginRequest, LoginResponse, UserResponse
from src.schema.http.common import OkResponse
from src.service import auth_task, log_task
from src.middleware.rbac import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login/", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """用户登录。"""
    result = auth_task.login(db, body.username, body.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    user = result["user"]
    log_task.record_operation(
        db,
        operator_id=user.id,
        action="login",
        target_type="auth",
        summary=f"用户登录：{user.username}",
        details={"username": user.username, "role": user.role},
    )
    db.commit()
    return LoginResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        user=UserResponse.model_validate(user),
    )


@router.post("/logout/", response_model=OkResponse)
def logout():
    """注销（客户端丢弃 token 即可）。"""
    return OkResponse()


@router.get("/me/", response_model=UserResponse)
def me(user=Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return UserResponse.model_validate(user)
