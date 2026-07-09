"""用户 REST API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.constants import API_PREFIX
from src.extensions import get_db
from src.schema.http.user import UserCreate, UserResponse
from src.service.user_task import create_user, list_users, UserNameConflictError

router = APIRouter(prefix="/users", tags=["用户"])


@router.post("", response_model=UserResponse, status_code=201)
def create(body: UserCreate, db: Session = Depends(get_db)):
    try:
        user = create_user(db, username=body.username, role=body.role)
        db.commit()
        return UserResponse.model_validate(user)
    except UserNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[UserResponse])
def list_all(db: Session = Depends(get_db)):
    return [UserResponse.model_validate(u) for u in list_users(db)]
