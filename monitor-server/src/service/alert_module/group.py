"""告警分组内部逻辑 —— AlertGroup CRUD + ResponseAction 绑定管理。"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.alert_group import AlertGroup
from src.models.response_action import ResponseAction
from src.repository.alert_group_repo import AlertGroupRepo
from src.repository.response_action_repo import ResponseActionRepo
from src.service.enum_task import EnumNameConflictError


def _repo(db: Session) -> AlertGroupRepo:
    return AlertGroupRepo(db)


# ── CRUD ────────────────────────────────────────


def create_group(db: Session, name: str) -> AlertGroup:
    try:
        return _repo(db).create(name=name)
    except IntegrityError:
        db.rollback()
        raise EnumNameConflictError(f"告警分组 '{name}' 已存在")


def list_groups(db: Session, page: int = 1, page_size: int = 100) -> tuple[list[AlertGroup], int]:
    return _repo(db).paginate(page=page, page_size=page_size)


def get_group(db: Session, id: int) -> AlertGroup | None:
    return _repo(db).get(id)


def update_group(db: Session, id: int, name: str) -> AlertGroup | None:
    repo = _repo(db)
    try:
        return repo.update(id, name=name)
    except IntegrityError:
        db.rollback()
        raise EnumNameConflictError(f"告警分组 '{name}' 已存在")


def delete_group(db: Session, id: int) -> bool:
    return _repo(db).delete(id)


# ── 绑定管理 ────────────────────────────────────


def bind_response(db: Session, group_id: int, response_id: int) -> list[ResponseAction] | None:
    """绑定响应动作到告警分组（幂等）。返回当前完整响应列表；分组不存在返回 None。"""
    group = _repo(db).get(group_id)
    if group is None:
        return None

    # 幂等：检查是否已绑定
    already_bound = any(r.id == response_id for r in group.responses)
    if not already_bound:
        response = ResponseActionRepo(db).get(response_id)
        if response is not None:
            group.responses.append(response)
            db.flush()

    # 重新加载以获取最新关联
    db.refresh(group)
    return list(group.responses)


def unbind_response(db: Session, group_id: int, response_id: int) -> bool:
    """解绑响应动作（幂等）。返回 True 表示分组存在；False 表示分组不存在。"""
    group = _repo(db).get(group_id)
    if group is None:
        return False

    group.responses = [r for r in group.responses if r.id != response_id]
    db.flush()
    return True


def get_group_responses(db: Session, group_id: int) -> list[ResponseAction] | None:
    """获取告警分组的当前响应动作列表；分组不存在返回 None。"""
    group = _repo(db).get(group_id)
    if group is None:
        return None
    return list(group.responses)
