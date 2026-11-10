from datetime import date
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.services.report_service import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{type}")
def get_report(
    type: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("reports", Action.VIEW)),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return report_service.get_report_data(
        db=db,
        report_type=type,
        branch_id=scope.selected_branch_id,
        start_date=start_date,
        end_date=end_date,
    )

