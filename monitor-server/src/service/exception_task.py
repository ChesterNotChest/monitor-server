"""异常定义管理服务。"""

from sqlalchemy.orm import Session

from src.repository.exception_def_repo import ExceptionDefRepo


def list_exceptions(db: Session):
    return ExceptionDefRepo(db).all()


def create_exception(db: Session, **kwargs):
    r = ExceptionDefRepo(db).create(**kwargs)
    db.commit()
    return r


def update_exception(db: Session, exc_id: int, **kwargs):
    r = ExceptionDefRepo(db).update(exc_id, **kwargs)
    db.commit()
    return r


def delete_exception(db: Session, exc_id: int) -> bool:
    ok = ExceptionDefRepo(db).delete(exc_id)
    db.commit()
    return ok
