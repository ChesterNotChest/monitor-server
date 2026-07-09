"""命名人物服务层门户。

编排命名人物 CRUD 与头像上传的业务流程。
通过 ``db: Session`` 参数接收数据库会话，委托 repository 和内部 logic 模块完成具体操作。
"""

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.repository.named_person_repo import NamedPersonRepo
from src.models.named_person import NamedPerson
from src.service.named_person_module.face_image import save_avatar, delete_avatar


def _repo(db: Session) -> NamedPersonRepo:
    return NamedPersonRepo(db)


class PersonNameConflictError(Exception):
    """姓名重复异常。"""

    pass


def create_person(db: Session, name: str) -> NamedPerson:
    """创建命名人物，姓名唯一性校验。"""
    repo = _repo(db)
    if repo.find_by_name(name):
        raise PersonNameConflictError(f"姓名 '{name}' 已存在")
    try:
        return repo.create(name=name)
    except IntegrityError:
        db.rollback()
        raise PersonNameConflictError(f"姓名 '{name}' 已存在")


def list_persons(db: Session, page: int = 1, page_size: int = 20) -> tuple[list[NamedPerson], int]:
    """分页查询命名人物列表。"""
    repo = _repo(db)
    return repo.paginate(page=page, page_size=page_size)


def get_person(db: Session, id: int) -> NamedPerson | None:
    """按 ID 查询单条记录。"""
    return _repo(db).get(id)


def update_person(db: Session, id: int, name: str | None) -> NamedPerson | None:
    """更新人物姓名。"""
    repo = _repo(db)
    if name is not None:
        existing = repo.find_by_name(name)
        if existing and existing.id != id:
            raise PersonNameConflictError(f"姓名 '{name}' 已被其他人物使用")
    try:
        return repo.update(id, name=name)
    except IntegrityError:
        db.rollback()
        raise PersonNameConflictError(f"姓名 '{name}' 已存在")


def delete_person(db: Session, id: int) -> bool:
    """删除人物及其头像文件。"""
    person = _repo(db).get(id)
    if person is None:
        return False
    if person.avatar_path:
        delete_avatar(id)
    return _repo(db).delete(id)


def upload_avatar(db: Session, id: int, file: UploadFile) -> NamedPerson | None:
    """上传/替换人物头像。"""
    person = _repo(db).get(id)
    if person is None:
        return None
    relative_path = save_avatar(id, file)
    return _repo(db).update(id, avatar_path=relative_path)
