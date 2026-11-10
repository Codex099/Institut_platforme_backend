from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.branch import Branch
from app.schemas.branch import BranchCreate, BranchResponse, BranchUpdate
from app.services.audit_service import audit_service

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get("", response_model=List[BranchResponse])
def list_branches(
    current_user: dict = Depends(require_permission("branches", Action.VIEW)),
    db: Session = Depends(get_db),
):
    return db.query(Branch).filter(Branch.is_archived.is_(False)).all()


@router.post("", response_model=BranchResponse)
def create_branch(
    data: BranchCreate,
    current_user: dict = Depends(require_permission("branches", Action.CREATE)),
    db: Session = Depends(get_db),
):
    branch = Branch(**data.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)

    audit_service.log(
        db=db,
        action="create_branch",
        entity="Branch",
        entity_id=branch.id,
        user_id=int(current_user["sub"]),
        after_json={"name": branch.name, "city": branch.city},
    )
    db.commit()
    return branch


@router.get("/{id}", response_model=BranchResponse)
def get_branch(
    id: int,
    current_user: dict = Depends(require_permission("branches", Action.VIEW)),
    db: Session = Depends(get_db),
):
    branch = db.query(Branch).filter(Branch.id == id, Branch.is_archived.is_(False)).first()
    if not branch:
        raise NotFoundError(message_key="resource_not_found")
    return branch


@router.put("/{id}", response_model=BranchResponse)
def update_branch(
    id: int,
    data: BranchUpdate,
    current_user: dict = Depends(require_permission("branches", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    branch = db.query(Branch).filter(Branch.id == id, Branch.is_archived.is_(False)).first()
    if not branch:
        raise NotFoundError(message_key="resource_not_found")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(branch, field, val)

    audit_service.log(
        db=db,
        action="update_branch",
        entity="Branch",
        entity_id=branch.id,
        user_id=int(current_user["sub"]),
    )
    db.commit()
    db.refresh(branch)
    return branch

