import os
from typing import BinaryIO, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.document import Document
from app.services.audit_service import audit_service
from app.services.storage_service import storage_service

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}


class DocumentService:
    @staticmethod
    def validate_file(upload: UploadFile):
        if upload.content_type not in ALLOWED_MIME_TYPES:
            raise BadRequestError(
                message_key="validation_error",
                details=f"Unsupported file type '{upload.content_type}'. Allowed types: PDF, Images, Excel.",
            )

    @classmethod
    def upload_document(
        cls,
        db: Session,
        upload_file: UploadFile,
        owner_type: str,
        owner_id: int,
        kind: str,
        uploaded_by: Optional[int] = None,
        visibility: str = "internal",
    ) -> Document:
        cls.validate_file(upload_file)

        # Check size
        upload_file.file.seek(0, os.SEEK_END)
        file_size = upload_file.file.tell()
        upload_file.file.seek(0)

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise BadRequestError(
                message_key="validation_error",
                details=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )

        file_key = storage_service.save_file(
            file_obj=upload_file.file,
            filename=upload_file.filename or "file.bin",
            mime_type=upload_file.content_type,
        )

        doc = Document(
            owner_type=owner_type,
            owner_id=owner_id,
            kind=kind,
            file_key=file_key,
            original_name=upload_file.filename or "uploaded_file",
            mime_type=upload_file.content_type or "application/octet-stream",
            file_size=file_size,
            uploaded_by=uploaded_by,
            visibility=visibility,
        )
        db.add(doc)
        db.flush()

        audit_service.log(
            db=db,
            action="upload_document",
            entity="Document",
            entity_id=doc.id,
            user_id=uploaded_by,
            after_json={"file_key": file_key, "owner_type": owner_type, "owner_id": owner_id},
        )

        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def get_document_for_download(db: Session, document_id: int) -> tuple[Document, str]:
        doc = db.query(Document).filter(Document.id == document_id, Document.is_archived.is_(False)).first()
        if not doc:
            raise NotFoundError(message_key="resource_not_found")
        file_path = storage_service.get_file_path(doc.file_key)
        return doc, file_path

    @staticmethod
    def delete_document(db: Session, document_id: int, actor_id: Optional[int] = None) -> None:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise NotFoundError(message_key="resource_not_found")

        doc.is_archived = True
        audit_service.log(
            db=db,
            action="archive_document",
            entity="Document",
            entity_id=doc.id,
            user_id=actor_id,
        )
        db.commit()


document_service = DocumentService()

