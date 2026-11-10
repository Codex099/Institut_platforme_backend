from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.level import Level
from app.schemas.common import StatusResponse
from app.schemas.level import LevelCreate, LevelResponse, LevelUpdate

router = APIRouter(prefix="/levels", tags=["Levels"])


@router.get("", response_model=List[LevelResponse])
def list_levels(
    course_id: Optional[int] = None,
    current_user: dict = Depends(require_permission("levels", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Level).filter(Level.is_archived.is_(False))
    if course_id:
        query = query.filter(Level.course_id == course_id)
    return query.all()


@router.post("", response_model=LevelResponse)
def create_level(
    data: LevelCreate,
    current_user: dict = Depends(require_permission("levels", Action.CREATE)),
    db: Session = Depends(get_db),
):
    level = Level(**data.model_dump())
    db.add(level)
    db.commit()
    db.refresh(level)
    return level


@router.get("/{id}", response_model=LevelResponse)
def get_level(
    id: int,
    current_user: dict = Depends(require_permission("levels", Action.VIEW)),
    db: Session = Depends(get_db),
):
    level = db.query(Level).filter(Level.id == id, Level.is_archived.is_(False)).first()
    if not level:
        raise NotFoundError(message_key="resource_not_found")
    return level


@router.put("/{id}", response_model=LevelResponse)
def update_level(
    id: int,
    data: LevelUpdate,
    current_user: dict = Depends(require_permission("levels", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    level = db.query(Level).filter(Level.id == id, Level.is_archived.is_(False)).first()
    if not level:
        raise NotFoundError(message_key="resource_not_found")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(level, field, val)

    db.commit()
    db.refresh(level)
    return level


@router.delete("/{id}", response_model=StatusResponse)
def delete_level(
    id: int,
    current_user: dict = Depends(require_permission("levels", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    level = db.query(Level).filter(Level.id == id, Level.is_archived.is_(False)).first()
    if not level:
        raise NotFoundError(message_key="resource_not_found")

    level.is_archived = True
    db.commit()
    return StatusResponse(code="SUCCESS", message="Level archived successfully.")

