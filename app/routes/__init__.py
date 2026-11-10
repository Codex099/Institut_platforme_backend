from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.public import router as public_router
from app.routes.branches import router as branches_router
from app.routes.users import router as users_router
from app.routes.permissions import router as permissions_router
from app.routes.students import router as students_router
from app.routes.parents import router as parents_router
from app.routes.teachers import router as teachers_router
from app.routes.courses import router as courses_router
from app.routes.levels import router as levels_router
from app.routes.groups import router as groups_router
from app.routes.rooms import router as rooms_router
from app.routes.schedules import router as schedules_router
from app.routes.sessions import router as sessions_router
from app.routes.closure_days import router as closure_days_router
from app.routes.enrollments import router as enrollments_router
from app.routes.documents import router as documents_router
from app.routes.attendance import router as attendance_router
from app.routes.payments import router as payments_router
from app.routes.installments import router as installments_router
from app.routes.expenses import router as expenses_router
from app.routes.cash_registers import router as cash_registers_router
from app.routes.fund_transfers import router as fund_transfers_router
from app.routes.payroll import router as payroll_router
from app.routes.announcements import router as announcements_router
from app.routes.notifications import router as notifications_router
from app.routes.dashboard import router as dashboard_router
from app.routes.reports import router as reports_router
from app.routes.imports import router as imports_router
from app.routes.exports import router as exports_router
from app.routes.audit_logs import router as audit_logs_router
from app.routes.settings import router as settings_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(public_router)
api_router.include_router(branches_router)
api_router.include_router(users_router)
api_router.include_router(permissions_router)
api_router.include_router(students_router)
api_router.include_router(parents_router)
api_router.include_router(teachers_router)
api_router.include_router(courses_router)
api_router.include_router(levels_router)
api_router.include_router(groups_router)
api_router.include_router(rooms_router)
api_router.include_router(schedules_router)
api_router.include_router(sessions_router)
api_router.include_router(closure_days_router)
api_router.include_router(enrollments_router)
api_router.include_router(documents_router)
api_router.include_router(attendance_router)
api_router.include_router(payments_router)
api_router.include_router(installments_router)
api_router.include_router(expenses_router)
api_router.include_router(cash_registers_router)
api_router.include_router(fund_transfers_router)
api_router.include_router(payroll_router)
api_router.include_router(announcements_router)
api_router.include_router(notifications_router)
api_router.include_router(dashboard_router)
api_router.include_router(reports_router)
api_router.include_router(imports_router)
api_router.include_router(exports_router)
api_router.include_router(audit_logs_router)
api_router.include_router(settings_router)

