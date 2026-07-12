"""告警分级管理服务。"""

from sqlalchemy.orm import Session

from src.repository.alert_group_repo import AlertGroupRepo


def list_alert_groups(db: Session):
    return AlertGroupRepo(db).with_responses()


def create_alert_group(db: Session, name: str):
    return AlertGroupRepo(db).create(name=name)


def update_alert_group(db: Session, group_id: int, name: str):
    return AlertGroupRepo(db).update(group_id, name=name)


def delete_alert_group(db: Session, group_id: int) -> bool:
    return AlertGroupRepo(db).delete(group_id)
