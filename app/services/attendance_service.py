from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import Role
from app.models.attendance import Attendance
from app.models.enrollment import Enrollment
from app.models.parent import StudentParent
from app.models.session import ClassSession
from app.models.setting import Setting
from app.models.student import Student
from app.models.teacher import Teacher
from app.schemas.attendance import AttendanceBatchRequest, AttendanceUpdate
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service


class AttendanceService:
    @staticmethod
    def get_edit_window_hours(db: Session, branch_id: int) -> int:
        setting = db.query(Setting).filter(Setting.key == "attendance_edit_window_hours", Setting.branch_id == branch_id).first()
        if not setting:
            setting = db.query(Setting).filter(Setting.key == "attendance_edit_window_hours", Setting.branch_id.is_(None)).first()
        if setting:
            try:
                return int(setting.value)
            except ValueError:
                pass
        return settings.ATTENDANCE_EDIT_WINDOW_HOURS

    @classmethod
    def record_batch_attendance(
        cls,
        db: Session,
        data: AttendanceBatchRequest,
        current_user: dict,
        ip_address: Optional[str] = None,
    ) -> List[Attendance]:
        """Record or update attendance for students in a session."""
        now = datetime.now(timezone.utc)
        user_id = int(current_user["sub"])
        user_role = current_user.get("role")

        session = db.query(ClassSession).filter(ClassSession.id == data.session_id).first()
        if not session:
            raise NotFoundError(message_key="resource_not_found")

        if session.status == "cancelled":
            raise BadRequestError(message_key="session_cancelled")

        # 1. Enforce teacher permission window and ownership
        if user_role == Role.TEACHER.value:
            teacher = db.query(Teacher).filter(Teacher.user_id == user_id).first()
            if not teacher or session.teacher_id != teacher.id:
                raise PermissionDeniedError(message_key="permission_denied", details="You can only submit attendance for your assigned sessions.")

            # Check time window
            window_hours = cls.get_edit_window_hours(db, session.group.branch_id)
            session_start_dt = datetime.combine(session.session_date, session.start_time, tzinfo=timezone.utc)
            if now > (session_start_dt + timedelta(hours=window_hours)):
                raise PermissionDeniedError(message_key="attendance_window_expired")

        # 2. Get list of valid confirmed students in this group
        confirmed_enrollments = (
            db.query(Enrollment.student_id)
            .filter(Enrollment.group_id == session.group_id, Enrollment.status == "confirmed")
            .all()
        )
        confirmed_student_ids = {e[0] for e in confirmed_enrollments}

        results = []
        for item in data.records:
            if item.student_id not in confirmed_student_ids:
                raise BadRequestError(
                    message_key="validation_error",
                    details=f"Student #{item.student_id} does not have a confirmed enrollment in this group.",
                )

            # Check if record already exists (anti-doublon)
            att = (
                db.query(Attendance)
                .filter(Attendance.session_id == session.id, Attendance.student_id == item.student_id)
                .first()
            )

            if att:
                before_status = att.status
                att.status = item.status
                att.notes = item.notes
                att.modified_by = user_id
                att.modified_at = now
                audit_service.log(
                    db=db,
                    action="update_attendance",
                    entity="Attendance",
                    entity_id=att.id,
                    user_id=user_id,
                    before_json={"status": before_status},
                    after_json={"status": att.status, "notes": att.notes},
                    ip_address=ip_address,
                )
            else:
                att = Attendance(
                    session_id=session.id,
                    student_id=item.student_id,
                    status=item.status,
                    method="manual",
                    notes=item.notes,
                    recorded_by=user_id,
                    recorded_at=now,
                )
                db.add(att)
                db.flush()
                audit_service.log(
                    db=db,
                    action="record_attendance",
                    entity="Attendance",
                    entity_id=att.id,
                    user_id=user_id,
                    after_json={"status": att.status, "session_id": session.id, "student_id": item.student_id},
                    ip_address=ip_address,
                )

            # Notify absence to student and validated parents
            if item.status == "absent":
                cls._notify_absence(db, att, session)

            results.append(att)

        # Mark session as held once attendance is recorded
        if session.status == "planned":
            session.status = "held"

        db.commit()
        return results

    @classmethod
    def update_attendance_record(
        cls,
        db: Session,
        attendance_id: int,
        data: AttendanceUpdate,
        current_user: dict,
        ip_address: Optional[str] = None,
    ) -> Attendance:
        """Manual attendance correction."""
        now = datetime.now(timezone.utc)
        user_id = int(current_user["sub"])
        user_role = current_user.get("role")

        att = db.query(Attendance).filter(Attendance.id == attendance_id).first()
        if not att:
            raise NotFoundError(message_key="resource_not_found")

        session = att.session
        if user_role == Role.TEACHER.value:
            teacher = db.query(Teacher).filter(Teacher.user_id == user_id).first()
            if not teacher or session.teacher_id != teacher.id:
                raise PermissionDeniedError(message_key="permission_denied")
            window_hours = cls.get_edit_window_hours(db, session.group.branch_id)
            session_start_dt = datetime.combine(session.session_date, session.start_time, tzinfo=timezone.utc)
            if now > (session_start_dt + timedelta(hours=window_hours)):
                raise PermissionDeniedError(message_key="attendance_window_expired")

        before_status = att.status
        att.status = data.status
        if data.notes is not None:
            att.notes = data.notes
        att.modified_by = user_id
        att.modified_at = now

        audit_service.log(
            db=db,
            action="modify_attendance_manual",
            entity="Attendance",
            entity_id=att.id,
            user_id=user_id,
            before_json={"status": before_status},
            after_json={"status": att.status, "reason": data.reason},
            ip_address=ip_address,
        )

        db.commit()
        db.refresh(att)
        return att

    @staticmethod
    def _notify_absence(db: Session, att: Attendance, session: ClassSession):
        student = db.query(Student).filter(Student.id == att.student_id).first()
        if not student:
            return

        recipients = []
        if student.user_id:
            recipients.append(student.user_id)

        parent_links = (
            db.query(StudentParent)
            .filter(StudentParent.student_id == student.id, StudentParent.is_validated.is_(True))
            .all()
        )
        for pl in parent_links:
            if pl.parent and pl.parent.user_id:
                recipients.append(pl.parent.user_id)

        notification_service.notify_multiple_users(
            db=db,
            user_ids=recipients,
            notif_type="absence_alert",
            title="Absence Notice",
            body=f"{student.first_name} {student.last_name} was marked absent on {session.session_date} for group {session.group.name}.",
            data={"session_id": session.id, "student_id": student.id},
        )


attendance_service = AttendanceService()

