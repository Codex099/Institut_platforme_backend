from typing import List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.attendance import Attendance
from app.models.session import ClassSession
from app.models.student import Student
from app.schemas.attendance import (
    AttendanceBatchRequest,
    AttendanceResponse,
    AttendanceUpdate,
)
from app.services.attendance_service import attendance_service

router = APIRouter(tags=["Attendance"])


@router.get("/sessions/{id}/attendance", response_model=List[AttendanceResponse])
def get_session_attendance(
    id: int,
    current_user: dict = Depends(require_permission("attendance", Action.VIEW)),
    db: Session = Depends(get_db),
):
    session = db.query(ClassSession).filter(ClassSession.id == id).first()
    if not session:
        raise NotFoundError(message_key="resource_not_found")

    records = db.query(Attendance).filter(Attendance.session_id == id).all()
    results = []
    for r in records:
        results.append(
            AttendanceResponse(
                id=r.id,
                session_id=r.session_id,
                student_id=r.student_id,
                student_name=f"{r.student.first_name} {r.student.last_name}" if r.student else None,
                student_number=r.student.student_number if r.student else None,
                status=r.status,
                method=r.method,
                notes=r.notes,
                recorded_by=r.recorded_by,
                recorded_at=r.recorded_at,
                modified_by=r.modified_by,
                modified_at=r.modified_at,
            )
        )
    return results


@router.post("/attendance/manual", response_model=List[AttendanceResponse])
def record_manual_attendance(
    data: AttendanceBatchRequest,
    request: Request,
    current_user: dict = Depends(require_permission("attendance", Action.CREATE)),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    saved_records = attendance_service.record_batch_attendance(
        db=db,
        data=data,
        current_user=current_user,
        ip_address=ip,
    )
    results = []
    for r in saved_records:
        results.append(
            AttendanceResponse(
                id=r.id,
                session_id=r.session_id,
                student_id=r.student_id,
                student_name=f"{r.student.first_name} {r.student.last_name}" if r.student else None,
                student_number=r.student.student_number if r.student else None,
                status=r.status,
                method=r.method,
                notes=r.notes,
                recorded_by=r.recorded_by,
                recorded_at=r.recorded_at,
                modified_by=r.modified_by,
                modified_at=r.modified_at,
            )
        )
    return results


@router.patch("/attendance/{id}", response_model=AttendanceResponse)
def update_attendance_record(
    id: int,
    data: AttendanceUpdate,
    request: Request,
    current_user: dict = Depends(require_permission("attendance", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    r = attendance_service.update_attendance_record(
        db=db,
        attendance_id=id,
        data=data,
        current_user=current_user,
        ip_address=ip,
    )
    return AttendanceResponse(
        id=r.id,
        session_id=r.session_id,
        student_id=r.student_id,
        student_name=f"{r.student.first_name} {r.student.last_name}" if r.student else None,
        student_number=r.student.student_number if r.student else None,
        status=r.status,
        method=r.method,
        notes=r.notes,
        recorded_by=r.recorded_by,
        recorded_at=r.recorded_at,
        modified_by=r.modified_by,
        modified_at=r.modified_at,
    )


@router.get("/students/{id}/attendance", response_model=List[AttendanceResponse])
def get_student_attendance_history(
    id: int,
    current_user: dict = Depends(require_permission("attendance", Action.VIEW)),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise NotFoundError(message_key="resource_not_found")

    records = db.query(Attendance).filter(Attendance.student_id == id).all()
    results = []
    for r in records:
        results.append(
            AttendanceResponse(
                id=r.id,
                session_id=r.session_id,
                student_id=r.student_id,
                student_name=f"{student.first_name} {student.last_name}",
                student_number=student.student_number,
                status=r.status,
                method=r.method,
                notes=r.notes,
                recorded_by=r.recorded_by,
                recorded_at=r.recorded_at,
                modified_by=r.modified_by,
                modified_at=r.modified_at,
            )
        )
    return results

