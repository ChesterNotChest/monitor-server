"""命名人物 REST API 路由。"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from src.constants import API_PREFIX, DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.extensions import get_db
from src.service.vision_module.vision_face.face_recognizer import notify_face_db_changed
from src.schema.http.named_person import (
    PersonCreate,
    PersonListResponse,
    PersonResponse,
    PersonUpdate,
)
from src.service.named_person_task import (
    PersonNameConflictError,
    create_person,
    delete_person,
    get_person,
    list_persons,
    update_person,
    upload_avatar,
)

router = APIRouter(prefix=f"{API_PREFIX}/persons", tags=["命名人物"])


def _to_response(person) -> PersonResponse:
    return PersonResponse.model_validate(person)


@router.post(
    "/",
    response_model=PersonResponse,
    status_code=201,
    responses={409: {"description": "名称已存在"}},
)
def create(body: PersonCreate, db: Session = Depends(get_db)):
    """创建命名人物。"""
    try:
        person = create_person(db, name=body.name)
        db.commit()
        notify_face_db_changed()
        return _to_response(person)
    except PersonNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/", response_model=PersonListResponse)
def list_all(
    db: Session = Depends(get_db),
    page: int = Query(DEFAULT_PAGE, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """分页查询命名人物列表。"""
    items, total = list_persons(db, page=page, page_size=page_size)
    return PersonListResponse(
        items=[_to_response(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{id}/",
    response_model=PersonResponse,
    responses={404: {"description": "命名人物不存在"}},
)
def get_one(id: int, db: Session = Depends(get_db)):
    """按 ID 查询命名人物详情。"""
    person = get_person(db, id)
    if person is None:
        raise HTTPException(status_code=404, detail="命名人物不存在")
    return _to_response(person)


@router.put(
    "/{id}/",
    response_model=PersonResponse,
    responses={404: {"description": "命名人物不存在"}, 409: {"description": "名称已存在"}},
)
def update(id: int, body: PersonUpdate, db: Session = Depends(get_db)):
    """更新命名人物信息。"""
    try:
        person = update_person(db, id, name=body.name)
        if person is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="命名人物不存在")
        db.commit()
        notify_face_db_changed()
        return _to_response(person)
    except PersonNameConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@router.delete(
    "/{id}/",
    status_code=204,
    responses={404: {"description": "命名人物不存在"}},
)
def delete(id: int, db: Session = Depends(get_db)):
    """删除命名人物及其头像文件。"""
    if not delete_person(db, id):
        raise HTTPException(status_code=404, detail="命名人物不存在")
    db.commit()
    notify_face_db_changed()


@router.post(
    "/{id}/avatar/",
    response_model=PersonResponse,
    responses={404: {"description": "命名人物不存在"}, 422: {"description": "文件格式不支持"}},
)
def upload(id: int, avatar: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传/替换人物头像。"""
    try:
        person = upload_avatar(db, id, avatar)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if person is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="命名人物不存在")
    db.commit()
    notify_face_db_changed()
    return _to_response(person)
