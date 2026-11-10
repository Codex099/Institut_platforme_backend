import io
import os
from typing import Any, Dict, List, Optional
import openpyxl
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.import_job import ImportJob
from app.models.student import Student
from app.services.audit_service import audit_service
from app.services.storage_service import storage_service


class ImportService:
    @staticmethod
    def get_template(resource: str) -> io.BytesIO:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = resource.capitalize()

        if resource == "students":
            headers = ["first_name", "last_name", "phone", "gender", "birth_date", "address"]
            ws.append(headers)
            ws.append(["Mohamed", "Benali", "0550123456", "male", "2005-04-12", "Chlef centre"])
        elif resource == "courses":
            headers = ["name_en", "name_ar", "type", "subject", "description_en"]
            ws.append(headers)
            ws.append(["General English B1", "الإنجليزية العامة B1", "language", "English", "Intermediate course"])
        else:
            ws.append(["id", "name", "notes"])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @classmethod
    def create_import_job(
        cls,
        db: Session,
        resource_type: str,
        branch_id: Optional[int],
        file_obj,
        filename: str,
        user_id: Optional[int] = None,
    ) -> ImportJob:
        file_key = storage_service.save_file(file_obj, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        job = ImportJob(
            type=resource_type,
            branch_id=branch_id,
            status="uploaded",
            file_key=file_key,
            created_by=user_id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def validate_and_preview(cls, db: Session, job_id: int) -> Dict[str, Any]:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise NotFoundError(message_key="resource_not_found")

        file_path = storage_service.get_file_path(job.file_key)
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
        except Exception as e:
            raise BadRequestError(message_key="validation_error", details=f"Cannot parse Excel file: {str(e)}")

        rows = list(ws.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            raise BadRequestError(message_key="validation_error", details="Excel file contains no data rows.")

        headers = [str(h).strip().lower() for h in rows[0] if h is not None]
        data_rows = rows[1:]

        errors = []
        preview_data = []
        valid_count = 0
        invalid_count = 0

        existing_phones = set()
        if job.type == "students":
            existing = db.query(Student.phone).filter(Student.phone.isnot(None)).all()
            existing_phones = {p[0] for p in existing}

        for idx, r in enumerate(data_rows, start=2):
            row_dict = {}
            for col_idx, h in enumerate(headers):
                if col_idx < len(r):
                    row_dict[h] = r[col_idx]

            row_errors = []
            if job.type == "students":
                if not row_dict.get("first_name"):
                    row_errors.append("first_name is required")
                if not row_dict.get("last_name"):
                    row_errors.append("last_name is required")
                phone = str(row_dict.get("phone") or "").strip()
                if phone and phone in existing_phones:
                    row_errors.append(f"Phone {phone} already registered in database")

            if row_errors:
                invalid_count += 1
                errors.append({"line": idx, "errors": row_errors, "row": row_dict})
            else:
                valid_count += 1
                if len(preview_data) < 20:
                    preview_data.append(row_dict)

        report = {
            "total_rows": len(data_rows),
            "valid_rows_count": valid_count,
            "invalid_rows_count": invalid_count,
            "errors": errors,
            "preview_data": preview_data,
        }

        job.status = "previewed"
        job.report_json = report
        db.commit()
        return report

    @classmethod
    def commit_import(cls, db: Session, job_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Commit validated rows into the database."""
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job or not job.report_json:
            raise NotFoundError(message_key="resource_not_found")

        if job.status == "committed":
            raise BadRequestError(message_key="validation_error", details="Import job has already been committed.")

        file_path = storage_service.get_file_path(job.file_key)
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        headers = [str(h).strip().lower() for h in rows[0] if h is not None]

        error_lines = {e["line"] for e in job.report_json.get("errors", [])}
        imported_count = 0

        if job.type == "students":
            for idx, r in enumerate(rows[1:], start=2):
                if idx in error_lines:
                    continue
                row_dict = dict(zip(headers, r))
                student = Student(
                    branch_id=job.branch_id or 1,
                    student_number=f"STD-IMP-{job.id}-{idx}",
                    first_name=str(row_dict.get("first_name", "")),
                    last_name=str(row_dict.get("last_name", "")),
                    phone=str(row_dict.get("phone", "")) if row_dict.get("phone") else None,
                    address=str(row_dict.get("address", "")) if row_dict.get("address") else None,
                    gender=str(row_dict.get("gender", "")) if row_dict.get("gender") else None,
                    status="candidate",
                )
                db.add(student)
                imported_count += 1

        job.status = "committed"
        audit_service.log(
            db=db,
            action="commit_import",
            entity="ImportJob",
            entity_id=job.id,
            user_id=user_id,
            after_json={"imported_count": imported_count},
        )

        db.commit()
        return {"status": "committed", "imported_count": imported_count}


import_service = ImportService()

