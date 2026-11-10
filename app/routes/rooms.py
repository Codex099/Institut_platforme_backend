from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.room import Room
from app.schemas.common import StatusResponse
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("", response_model=List[RoomResponse])
def list_rooms(
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("rooms", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Room).filter(Room.is_archived.is_(False))
    query = scope.apply_query_filter(query, Room)
    return query.all()


@router.post("", response_model=RoomResponse)
def create_room(
    data: RoomCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("rooms", Action.CREATE)),
    db: Session = Depends(get_db),
):
    scope.ensure_access(data.branch_id)
    room = Room(**data.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.get("/{id}", response_model=RoomResponse)
def get_room(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("rooms", Action.VIEW)),
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(Room.id == id, Room.is_archived.is_(False)).first()
    if not room:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(room.branch_id)
    return room


@router.put("/{id}", response_model=RoomResponse)
def update_room(
    id: int,
    data: RoomUpdate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("rooms", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(Room.id == id, Room.is_archived.is_(False)).first()
    if not room:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(room.branch_id)

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(room, field, val)

    db.commit()
    db.refresh(room)
    return room


@router.delete("/{id}", response_model=StatusResponse)
def delete_room(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("rooms", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(Room.id == id, Room.is_archived.is_(False)).first()
    if not room:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(room.branch_id)

    room.is_archived = True
    db.commit()
    return StatusResponse(code="SUCCESS", message="Room archived successfully.")

