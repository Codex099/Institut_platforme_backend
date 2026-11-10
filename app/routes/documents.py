from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.schemas.common import StatusResponse
from app.schemas.document import DocumentResponse
from app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    owner_type: str = Form(...),
    owner_id: int = Form(...),
    kind: str = Form(...),
    visibility: str = Form("internal"),
    current_user: dict = Depends(require_permission("documents", Action.CREATE)),
    db: Session = Depends(get_db),
):
    return document_service.upload_document(
        db=db,
        upload_file=file,
        owner_type=owner_type,
        owner_id=owner_id,
        kind=kind,
        uploaded_by=int(current_user["sub"]),
        visibility=visibility,
    )


@router.get("/{id}/download")
def download_document(
    id: int,
    current_user: dict = Depends(require_permission("documents", Action.VIEW)),
    db: Session = Depends(get_db),
):
    doc, file_path = document_service.get_document_for_download(db, id)
    return FileResponse(
        path=file_path,
        filename=doc.original_name,
        media_type=doc.mime_type,
    )


@router.delete("/{id}", response_model=StatusResponse)
def delete_document(
    id: int,
    current_user: dict = Depends(require_permission("documents", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    document_service.delete_document(db, id, actor_id=int(current_user["sub"]))
    return StatusResponse(code="SUCCESS", message="Document archived successfully.")

