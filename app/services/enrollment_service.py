from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, BadRequestError
from app.core.permissions import Role
from app.models.branch import Branch
from app.models.enrollment import Enrollment
from app.models.group import Group
from app.models.level import Level
from app.models.payment import Payment
from app.models.schedule import ScheduleSlot
from app.models.setting import Setting
from app.models.student import Student
from app.schemas.enrollment import EnrollmentCreate, PublicPreregistrationRequest
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service


class EnrollmentService:
    @staticmethod
    def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @staticmethod
    def get_reservation_hours(db: Session, branch_id: int) -> int:
        setting = db.query(Setting).filter(Setting.key == "reservation_hours", Setting.branch_id == branch_id).first()
        if not setting:
            setting = db.query(Setting).filter(Setting.key == "reservation_hours", Setting.branch_id.is_(None)).first()
        if setting:
            try:
                return int(setting.value)
            except ValueError:
                pass
        return settings.DEFAULT_RESERVATION_HOURS

    @staticmethod
    def get_deposit_min(db: Session, branch_id: int) -> float:
        setting = db.query(Setting).filter(Setting.key == "deposit_min", Setting.branch_id == branch_id).first()
        if not setting:
            setting = db.query(Setting).filter(Setting.key == "deposit_min", Setting.branch_id.is_(None)).first()
        if setting:
            try:
                return float(setting.value)
            except ValueError:
                pass
        return float(settings.DEFAULT_DEPOSIT_MIN)

    @classmethod
    def get_effective_capacity(cls, db: Session, group: Group) -> int:
        if group.capacity and group.capacity > 0:
            return group.capacity
        if group.level and group.level.default_capacity and group.level.default_capacity > 0:
            return group.level.default_capacity
        setting = db.query(Setting).filter(Setting.key == "default_group_capacity", Setting.branch_id == group.branch_id).first()
        if not setting:
            setting = db.query(Setting).filter(Setting.key == "default_group_capacity", Setting.branch_id.is_(None)).first()
        if setting:
            try:
                return int(setting.value)
            except ValueError:
                pass
        return settings.DEFAULT_GROUP_CAPACITY

    @classmethod
    def get_occupied_spots(cls, db: Session, group_id: int, now: Optional[datetime] = None) -> Tuple[int, int, int]:
        """Returns (confirmed_count, reserved_active_count, total_occupied)."""
        if now is None:
            now = datetime.now(timezone.utc)

        confirmed = (
            db.query(func.count(Enrollment.id))
            .filter(Enrollment.group_id == group_id, Enrollment.status == "confirmed")
            .scalar()
            or 0
        )

        reserved = (
            db.query(func.count(Enrollment.id))
            .filter(
                Enrollment.group_id == group_id,
                Enrollment.status == "pending_payment",
                Enrollment.reserved_until > now,
            )
            .scalar()
            or 0
        )

        return confirmed, reserved, confirmed + reserved

    @classmethod
    def check_student_schedule_overlap(
        cls, db: Session, student_id: int, target_group_id: int, now: Optional[datetime] = None
    ) -> List[dict]:
        """Verify if student already has active enrollments overlapping with target group's weekly slots."""
        if now is None:
            now = datetime.now(timezone.utc)

        target_slots = db.query(ScheduleSlot).filter(ScheduleSlot.group_id == target_group_id).all()
        if not target_slots:
            return []

        # Find existing active or valid pending enrollments for student
        active_enrollments = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id == student_id,
                Enrollment.group_id != target_group_id,
                or_(
                    Enrollment.status == "confirmed",
                    (Enrollment.status == "pending_payment") & (Enrollment.reserved_until > now),
                ),
            )
            .all()
        )

        overlaps = []
        for enr in active_enrollments:
            existing_slots = db.query(ScheduleSlot).filter(ScheduleSlot.group_id == enr.group_id).all()
            for t_slot in target_slots:
                for e_slot in existing_slots:
                    if t_slot.weekday == e_slot.weekday:
                        # Check time interval overlap: (start1 < end2) and (end1 > start2)
                        if t_slot.start_time < e_slot.end_time and t_slot.end_time > e_slot.start_time:
                            overlaps.append({
                                "conflict_group_id": enr.group_id,
                                "weekday": t_slot.weekday,
                                "target_window": f"{t_slot.start_time} - {t_slot.end_time}",
                                "existing_window": f"{e_slot.start_time} - {e_slot.end_time}",
                            })
        return overlaps

    @classmethod
    def create_enrollment(
        cls,
        db: Session,
        data: EnrollmentCreate,
        creator_id: Optional[int] = None,
        creator_role: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Enrollment:
        """Create enrollment reservation with SELECT FOR UPDATE row locking."""
        now = datetime.now(timezone.utc)

        # 1. Lock group row to prevent race conditions on capacity
        group = (
            db.query(Group)
            .filter(Group.id == data.group_id, Group.is_archived.is_(False))
            .with_for_update()
            .first()
        )
        if not group:
            raise NotFoundError(message_key="group_not_found")

        # 2. Check student schedule overlap
        overlaps = cls.check_student_schedule_overlap(db, data.student_id, data.group_id, now)
        if overlaps and not data.allow_overlap:
            raise ConflictError(
                message_key="student_schedule_conflict",
                details={"overlaps": overlaps},
            )
        elif overlaps and data.allow_overlap:
            # Only directors can override schedule overlap
            if creator_role not in (Role.SUPER_ADMIN.value, Role.BRANCH_DIRECTOR.value):
                raise PermissionDeniedError(message_key="permission_denied", details="Only directors can force overlap.")

        # 3. Check capacity
        effective_cap = cls.get_effective_capacity(db, group)
        _, _, occupied = cls.get_occupied_spots(db, group.id, now)

        if occupied >= effective_cap:
            if not data.allow_over_capacity:
                raise ConflictError(
                    message_key="group_capacity_exceeded",
                    details={"capacity": effective_cap, "occupied": occupied},
                )
            # Check over-capacity permissions
            if creator_role not in (Role.SUPER_ADMIN.value, Role.BRANCH_DIRECTOR.value):
                raise PermissionDeniedError(message_key="group_over_capacity_unauthorized")
            if not data.over_capacity_reason:
                raise BadRequestError(
                    message_key="validation_error",
                    details="A mandatory reason is required for over-capacity enrollment.",
                )

        # 4. Generate unique reference
        branch = db.query(Branch).filter(Branch.id == group.branch_id).first()
        b_code = (branch.code or "BR").upper()
        ref = f"ENR-{now.year}-{b_code}-{uuid.uuid4().hex[:6].upper()}"

        # 5. Calculate reservation deadline
        res_hours = cls.get_reservation_hours(db, group.branch_id)
        reserved_until = now + timedelta(hours=res_hours)

        enrollment = Enrollment(
            reference=ref,
            student_id=data.student_id,
            group_id=data.group_id,
            branch_id=group.branch_id,
            source=data.source,
            status="pending_payment",
            reserved_until=reserved_until,
            total_fee=data.total_fee,
            discount_amount=data.discount_amount,
            discount_reason=data.discount_reason,
            allow_over_capacity=data.allow_over_capacity,
            over_capacity_reason=data.over_capacity_reason,
            created_by=creator_id,
        )
        db.add(enrollment)
        db.flush()

        audit_service.log(
            db=db,
            action="create_enrollment_reservation",
            entity="Enrollment",
            entity_id=enrollment.id,
            user_id=creator_id,
            after_json={
                "reference": ref,
                "student_id": enrollment.student_id,
                "group_id": enrollment.group_id,
                "reserved_until": str(reserved_until),
                "allow_over_capacity": enrollment.allow_over_capacity,
                "allow_overlap": data.allow_overlap,
            },
            ip_address=ip_address,
        )

        db.commit()
        db.refresh(enrollment)
        return enrollment

    @classmethod
    def public_preregistration(cls, db: Session, data: PublicPreregistrationRequest, ip_address: Optional[str] = None) -> Enrollment:
        """Handle public website candidate registration and group reservation."""
        now = datetime.now(timezone.utc)

        # 1. Lock group
        group = db.query(Group).filter(Group.id == data.group_id, Group.is_archived.is_(False)).with_for_update().first()
        if not group:
            raise NotFoundError(message_key="group_not_found")

        # Check capacity (public cannot exceed capacity)
        effective_cap = cls.get_effective_capacity(db, group)
        _, _, occupied = cls.get_occupied_spots(db, group.id, now)
        if occupied >= effective_cap:
            raise ConflictError(message_key="group_capacity_exceeded")

        # 2. Find or create student
        student = None
        if data.phone:
            student = db.query(Student).filter(Student.phone == data.phone, Student.branch_id == data.branch_id).first()

        if not student:
            branch = db.query(Branch).filter(Branch.id == data.branch_id).first()
            b_code = (branch.code or "BR").upper()
            std_num = f"STD-{now.year}-{b_code}-{uuid.uuid4().hex[:6].upper()}"
            student = Student(
                branch_id=data.branch_id,
                student_number=std_num,
                first_name=data.first_name,
                last_name=data.last_name,
                birth_date=data.birth_date,
                gender=data.gender,
                phone=data.phone,
                address=data.address,
                status="candidate",
            )
            db.add(student)
            db.flush()

        # 3. Create provisional reservation
        level = db.query(Level).filter(Level.id == group.level_id).first()
        total_fee = level.price + level.registration_fee if level else 0.00

        enr_create = EnrollmentCreate(
            student_id=student.id,
            group_id=group.id,
            branch_id=group.branch_id,
            source="online",
            total_fee=total_fee,
            discount_amount=0.00,
        )

        enrollment = cls.create_enrollment(
            db=db,
            data=enr_create,
            creator_id=None,
            creator_role="public",
            ip_address=ip_address,
        )
        return enrollment

    @classmethod
    def confirm_enrollment(
        cls,
        db: Session,
        enrollment_id: int,
        initial_payment_amount: float,
        payment_method: str,
        confirmer_id: int,
        cash_register_id: Optional[int] = None,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Enrollment:
        """Confirm enrollment after ensuring minimum deposit is paid."""
        now = datetime.now(timezone.utc)
        enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).with_for_update().first()
        if not enrollment:
            raise NotFoundError(message_key="enrollment_not_found")

        if enrollment.status == "confirmed":
            raise ConflictError(message_key="enrollment_already_confirmed")

        res_until = cls._ensure_utc(enrollment.reserved_until)
        if enrollment.status == "expired" or (enrollment.status == "pending_payment" and res_until and res_until < now):
            enrollment.status = "expired"
            db.commit()
            raise ConflictError(message_key="reservation_expired")

        # Verify minimum deposit requirement
        min_dep = cls.get_deposit_min(db, enrollment.branch_id)
        if float(initial_payment_amount) < min_dep:
            raise BadRequestError(
                message_key="enrollment_deposit_insufficient",
                details={"minimum_required": min_dep, "provided": float(initial_payment_amount)},
            )

        # Transition status
        enrollment.status = "confirmed"
        enrollment.confirmed_by = confirmer_id
        enrollment.confirmed_at = now

        # Update student status to active
        if enrollment.student:
            enrollment.student.status = "active"

        audit_service.log(
            db=db,
            action="confirm_enrollment",
            entity="Enrollment",
            entity_id=enrollment.id,
            user_id=confirmer_id,
            after_json={"status": "confirmed", "confirmed_at": str(now)},
            ip_address=ip_address,
        )

        db.commit()
        db.refresh(enrollment)
        return enrollment

    @staticmethod
    def cancel_enrollment(db: Session, enrollment_id: int, reason: str, canceller_id: int) -> Enrollment:
        enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if not enrollment:
            raise NotFoundError(message_key="enrollment_not_found")

        enrollment.status = "cancelled"
        audit_service.log(
            db=db,
            action="cancel_enrollment",
            entity="Enrollment",
            entity_id=enrollment.id,
            user_id=canceller_id,
            after_json={"status": "cancelled", "reason": reason},
        )
        db.commit()
        db.refresh(enrollment)
        return enrollment

    @staticmethod
    def extend_reservation(db: Session, enrollment_id: int, additional_hours: int, actor_id: int) -> Enrollment:
        now = datetime.now(timezone.utc)
        enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if not enrollment:
            raise NotFoundError(message_key="enrollment_not_found")
        if enrollment.status != "pending_payment":
            raise BadRequestError(message_key="validation_error", details="Only pending reservations can be extended.")

        res_until = cls._ensure_utc(enrollment.reserved_until) or now
        base_time = max(res_until, now)
        enrollment.reserved_until = base_time + timedelta(hours=additional_hours)
        audit_service.log(
            db=db,
            action="extend_reservation",
            entity="Enrollment",
            entity_id=enrollment.id,
            user_id=actor_id,
            after_json={"new_reserved_until": str(enrollment.reserved_until), "hours_added": additional_hours},
        )
        db.commit()
        db.refresh(enrollment)
        return enrollment

    @staticmethod
    def expire_pending_reservations(db: Session) -> int:
        """Scheduled job: expire reservations older than reserved_until."""
        now = datetime.now(timezone.utc)
        expired_reservations = (
            db.query(Enrollment)
            .filter(
                Enrollment.status == "pending_payment",
                Enrollment.reserved_until <= now,
            )
            .all()
        )
        count = 0
        for enr in expired_reservations:
            enr.status = "expired"
            count += 1
            if enr.student and enr.student.user_id:
                notification_service.notify_user(
                    db=db,
                    user_id=enr.student.user_id,
                    notif_type="reservation_expired",
                    title="Reservation Expired",
                    body=f"Your provisional reservation {enr.reference} has expired.",
                )
        if count > 0:
            db.commit()
        return count


enrollment_service = EnrollmentService()
