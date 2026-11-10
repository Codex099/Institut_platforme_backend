from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import BadRequestError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.student import Student
from app.services.export_service import export_service

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.get("/{resource}")
def export_data(
    resource: str,
    format: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("exports", Action.EXPORT)),
    db: Session = Depends(get_db),
):
    if resource == "students":
        query = db.query(Student).filter(Student.is_archived.is_(False))
        query = scope.apply_query_filter(query, Student)
        students = query.all()

        headers = ["Numéro", "Nom", "Prénom", "Téléphone", "Statut", "Date Naissance"]
        rows = [
            [s.student_number, s.last_name, s.first_name, s.phone or "", s.status, str(s.birth_date or "")]
            for s in students
        ]
        title = "Liste des Étudiants"
    else:
        raise BadRequestError(message_key="validation_error", details=f"Export for '{resource}' not supported.")

    if format == "xlsx":
        buf = export_service.export_to_excel(title, headers, rows)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{resource}.xlsx"'},
        )
    else:
        buf = export_service.export_to_pdf(title, headers, rows)
        return Response(
            content=buf.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{resource}.pdf"'},
        )
