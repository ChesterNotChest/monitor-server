"""用户管理 API 路由 —— 运维员专有。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.auth_schema import UserResponse
from src.service import user_service
from src.constants import Role

router = APIRouter(prefix="/users", tags=["用户管理"])
_perm = Depends(require_permission("user:manage"))


@router.get("", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _user=_perm):
    return user_service.list_users(db)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    username: str,
    password: str,
    role: str = Role.SECURITY_GUARD,
    db: Session = Depends(get_db),
    _user=_perm,
):
    """创建用户。role 取 security_guard / manager / operator。"""
    if role not in [r.value for r in Role]:
        raise HTTPException(400, f"无效角色: {role}")
    try:
        return user_service.create_user(db, username, password, role)
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.put("/{user_id}/role", response_model=UserResponse)
def update_role(user_id: int, role: str, db: Session = Depends(get_db), _user=_perm):
    if role not in [r.value for r in Role]:
        raise HTTPException(400, f"无效角色: {role}")
    result = user_service.update_role(db, user_id, role)
    if result is None:
        raise HTTPException(404, "用户不存在")
    return result


@router.put("/{user_id}/deactivate")
def deactivate_user(user_id: int, db: Session = Depends(get_db), _user=_perm):
    if not user_service.deactivate_user(db, user_id):
        raise HTTPException(404, "用户不存在")
    return {"ok": True}
