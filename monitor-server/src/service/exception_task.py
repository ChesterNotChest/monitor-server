"""异常定义管理服务。"""

from sqlalchemy.orm import Session

from src.repository.exception_def_repo import ExceptionDefRepo


def list_exceptions(db: Session):
    return ExceptionDefRepo(db).all()


def create_exception(db: Session, **kwargs):
    return ExceptionDefRepo(db).create(**kwargs)


def update_exception(db: Session, exc_id: int, **kwargs):
    return ExceptionDefRepo(db).update(exc_id, **kwargs)


def delete_exception(db: Session, exc_id: int) -> bool:
    return ExceptionDefRepo(db).delete(exc_id)
