"""用户管理 API 路由 —— 运维员专有。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.extensions import get_db
from src.middleware.rbac import require_permission
from src.schema.http.auth_schema import UserResponse
from src.schema.http.common import OkResponse
from src.service import user_task
from src.constants import Role

router = APIRouter(prefix="/users", tags=["用户管理"])
_perm = Depends(require_permission("user:manage"))


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _user=_perm):
    """列出所有用户。

    **权限**: user:manage
    """
    return user_task.list_users(db)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
    responses={400: {"description": "无效角色"}, 409: {"description": "用户名已存在"}},
)
def create_user(
    username: str,
    password: str,
    role: str = Role.SECURITY_GUARD,
    dingtalk_mobile: str | None = None,
    supervisor_id: str | None = None,
    db: Session = Depends(get_db),
    _user=_perm,
):
    """创建用户。role 取 security_guard / manager / operator。

    **权限**: user:manage
    """
    if role not in [r.value for r in Role]:
        raise HTTPException(400, f"无效角色: {role}")
    sup_id: int | None = None
    if supervisor_id and supervisor_id.strip():
        try:
            sup_id = int(supervisor_id)
        except ValueError:
            pass
    try:

=======
        result = user_task.create_user(db, username, password, role,
                                     dingtalk_mobile=dingtalk_mobile,
                                     supervisor_id=sup_id)
        db.commit()
        return result

    except ValueError as e:
        raise HTTPException(409, str(e))


@router.put(

    "/{user_id}",
    response_model=UserResponse,
    responses={404: {"description": "用户不存在"}},
)
def update_user(
    user_id: int,
    role: str | None = None,
    dingtalk_mobile: str | None = None,
    supervisor_id: str | None = None,
    db: Session = Depends(get_db),
    _user=_perm,
):
    """更新用户信息（角色、钉钉手机号、上级）。所有参数可选。

    **权限**: user:manage
    """
    # "0" 或 空字符串 → None，其他数字直接使用
    sup_id: int | None = None
    if supervisor_id and supervisor_id.strip() and supervisor_id.strip() != "0":
        try:
            sup_id = int(supervisor_id)
        except ValueError:
            pass
    result = user_task.update_user(db, user_id,
                                   role=role,
                                   dingtalk_mobile=dingtalk_mobile,
                                   supervisor_id=sup_id)
    if result is None:
        raise HTTPException(404, "用户不存在")
    return result


@router.put(

=======
    "/{user_id}/role/",

    response_model=UserResponse,
    responses={400: {"description": "无效角色"}, 404: {"description": "用户不存在"}},
)
def update_role(user_id: int, role: str, db: Session = Depends(get_db), _user=_perm):
    """修改用户角色。

    **权限**: user:manage
    """
    if role not in [r.value for r in Role]:
        raise HTTPException(400, f"无效角色: {role}")
    result = user_task.update_role(db, user_id, role)
    if result is None:
        raise HTTPException(404, "用户不存在")
    db.commit()
    return result


@router.put(
    "/{user_id}/deactivate/",
    response_model=OkResponse,
    responses={404: {"description": "用户不存在"}},
)
def deactivate_user(user_id: int, db: Session = Depends(get_db), _user=_perm):
    """停用用户（软删除：is_active=false）。

    **权限**: user:manage
    """
    if not user_task.deactivate_user(db, user_id):
        raise HTTPException(404, "用户不存在")
    db.commit()
    return OkResponse()
