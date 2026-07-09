"""RBAC 中间件 —— JWT 认证 + 角色/权限检查。

用法::

    @router.get("/fences")
    def list_fences(
        db: Session = Depends(get_db),
        user: User = Depends(require_permission("fence:manage")),
    ):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.constants import Role
from src.extensions import get_db
from src.repository.user_repo import UserRepo
from src.service.auth_task import verify_token

oauth2_scheme = HTTPBearer()


# ── 权限矩阵 ─────────────────────────────────────────

PERMISSIONS: dict[str, set[Role]] = {
    "dashboard:view":    {Role.SECURITY_GUARD, Role.MANAGER, Role.OPERATOR},
    "monitor:view":      {Role.SECURITY_GUARD, Role.MANAGER},
    "monitor:replay":    {Role.SECURITY_GUARD, Role.MANAGER},
    "alert:list":        {Role.SECURITY_GUARD, Role.MANAGER, Role.OPERATOR},
    "alert:handle":      {Role.SECURITY_GUARD, Role.MANAGER},
    "fence:manage":      {Role.SECURITY_GUARD},
    "detection:manage":  {Role.MANAGER},
    "exception:manage":  {Role.MANAGER, Role.OPERATOR},
    "alert_group:manage": {Role.MANAGER, Role.OPERATOR},
    "report:view":       {Role.MANAGER},
    "device:onboard":    {Role.OPERATOR},
    "device:list":       {Role.OPERATOR},
    "device:health":     {Role.OPERATOR},
    "log:view":          {Role.OPERATOR},
    "user:manage":       {Role.OPERATOR},
}


# ── 依赖注入 ──────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """解码 JWT，从 DB 加载 User 实例。401 如果 token 无效。"""
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭据",
        )

    user_id = int(payload.get("sub", 0))
    user = UserRepo(db).get(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被停用",
        )
    return user


def require_role(*roles: Role):
    """返回 Depends 可用的依赖。403 如果角色不匹配。"""

    def _check(user = Depends(get_current_user)):
        user_role = Role(user.role)
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {[r.value for r in roles]} 角色权限",
            )
        return user

    return _check


def require_permission(perm: str):
    """返回 Depends 可用的依赖。403 如果角色无此权限。"""

    allowed_roles = PERMISSIONS.get(perm, set())

    def _check(user = Depends(get_current_user)):
        user_role = Role(user.role)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"无权执行操作: {perm}",
            )
        return user

    return _check
