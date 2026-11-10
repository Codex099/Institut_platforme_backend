from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.schemas.dashboard import BranchDashboardResponse, GeneralDashboardResponse
from app.services.report_service import report_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/general", response_model=GeneralDashboardResponse)
def get_general_dashboard(
    current_user: dict = Depends(require_permission("dashboard", Action.VIEW)),
    db: Session = Depends(get_db),
):
    return report_service.get_general_dashboard(db)


@router.get("/branch", response_model=BranchDashboardResponse)
def get_branch_dashboard(
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("dashboard", Action.VIEW)),
    db: Session = Depends(get_db),
):
    branch_id = scope.selected_branch_id or (scope.allowed_branch_ids[0] if scope.allowed_branch_ids else 1)
    return report_service.get_branch_dashboard(db, branch_id)

