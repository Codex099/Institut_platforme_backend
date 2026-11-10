from typing import Any, Dict
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.import_job import ImportJob
from app.schemas.import_job import ImportJobResponse, ImportPreviewResponse
from app.services.import_service import import_service

router = APIRouter(prefix="/imports", tags=["Imports"])


@router.get("/templates/{resource}")
def download_import_template(
    resource: str,
    current_user: dict = Depends(require_permission("imports", Action.VIEW)),
):
    buf = import_service.get_template(resource)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="template_{resource}.xlsx"'},
    )


@router.post("", response_model=ImportJobResponse)
def upload_import_file(
    type: str = Form(...),
    branch_id: int = Form(1),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_permission("imports", Action.CREATE)),
    db: Session = Depends(get_db),
):
    return import_service.create_import_job(
        db=db,
        resource_type=type,
        branch_id=branch_id,
        file_obj=file.file,
        filename=file.filename or "import.xlsx",
        user_id=int(current_user["sub"]),
    )


@router.get("/{id}/preview", response_model=ImportPreviewResponse)
def preview_import(
    id: int,
    current_user: dict = Depends(require_permission("imports", Action.VIEW)),
    db: Session = Depends(get_db),
):
    res = import_service.validate_and_preview(db, id)
    return ImportPreviewResponse(
        job_id=id,
        total_rows=res["total_rows"],
        valid_rows_count=res["valid_rows_count"],
        invalid_rows_count=res["invalid_rows_count"],
        errors=res["errors"],
        preview_data=res["preview_data"],
    )


@router.post("/{id}/commit")
def commit_import(
    id: int,
    current_user: dict = Depends(require_permission("imports", Action.VALIDATE)),
    db: Session = Depends(get_db),
):
    return import_service.commit_import(db, id, user_id=int(current_user["sub"]))


@router.get("/{id}/report")
def get_import_report(
    id: int,
    current_user: dict = Depends(require_permission("imports", Action.VIEW)),
    db: Session = Depends(get_db),
):
    job = db.query(ImportJob).filter(ImportJob.id == id).first()
    if not job:
        raise NotFoundError(message_key="resource_not_found")
    return job.report_json or {}

