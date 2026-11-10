from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate, ExpenseResponse

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("", response_model=List[ExpenseResponse])
def list_expenses(
    category: Optional[str] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("expenses", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Expense).filter(Expense.is_archived.is_(False))
    query = scope.apply_query_filter(query, Expense)
    if category:
        query = query.filter(Expense.category == category)
    return query.order_by(Expense.expense_date.desc()).all()


@router.post("", response_model=ExpenseResponse)
def create_expense(
    data: ExpenseCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("expenses", Action.CREATE)),
    db: Session = Depends(get_db),
):
    scope.ensure_access(data.branch_id)
    expense = Expense(**data.model_dump(), created_by=int(current_user["sub"]))
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense

