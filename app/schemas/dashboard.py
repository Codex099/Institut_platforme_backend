from typing import Dict, List
from pydantic import BaseModel, condecimal


class BranchMetricItem(BaseModel):
    branch_id: int
    branch_name: str
    students_count: int
    active_groups_count: int
    total_revenue: condecimal(max_digits=12, decimal_places=2)
    total_expenses: condecimal(max_digits=12, decimal_places=2)
    cash_balance: condecimal(max_digits=12, decimal_places=2)


class GeneralDashboardResponse(BaseModel):
    total_branches: int
    total_students: int
    new_students_this_month: int
    pending_preregistrations: int
    total_teachers: int
    total_agents: int
    active_groups: int
    total_revenue: condecimal(max_digits=12, decimal_places=2)
    total_expenses: condecimal(max_digits=12, decimal_places=2)
    total_cash_balances: condecimal(max_digits=12, decimal_places=2)
    total_unpaid_debt: condecimal(max_digits=12, decimal_places=2)
    branch_comparison: List[BranchMetricItem]


class BranchDashboardResponse(BaseModel):
    branch_id: int
    branch_name: str
    total_students: int
    active_groups: int
    pending_preregistrations: int
    total_revenue: condecimal(max_digits=12, decimal_places=2)
    total_expenses: condecimal(max_digits=12, decimal_places=2)
    cash_register_balance: condecimal(max_digits=12, decimal_places=2)
    total_unpaid_debt: condecimal(max_digits=12, decimal_places=2)
    sessions_today_count: int

