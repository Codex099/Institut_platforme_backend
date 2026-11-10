from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, BadRequestError
from app.models.closure_day import ClosureDay
from app.models.enrollment import Enrollment
from app.models.group import Group
from app.models.parent import StudentParent
from app.models.room import Room
from app.models.schedule import ScheduleSlot
from app.models.session import ClassSession
from app.models.setting import Setting
from app.models.teacher import Teacher
from app.schemas.schedule import CheckConflictResponse, ConflictItem, ScheduleSlotCreate, ScheduleSlotUpdate
from app.schemas.session import CancelSessionRequest, GenerateSessionsResponse, RescheduleSessionRequest
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service


class ScheduleService:
    @staticmethod
    def get_room_capacity_policy(db: Session, branch_id: int) -> str:
        setting = db.query(Setting).filter(Setting.key == "room_capacity_policy", Setting.branch_id == branch_id).first()
        if not setting:
            setting = db.query(Setting).filter(Setting.key == "room_capacity_policy", Setting.branch_id.is_(None)).first()
        return setting.value.lower() if setting else "warn"

    @classmethod
    def check_slot_conflicts(
        cls,
        db: Session,
        group_id: int,
        room_id: int,
        teacher_id: int,
        weekday: int,
        start_time: time,
        end_time: time,
        exclude_slot_id: Optional[int] = None,
    ) -> List[ConflictItem]:
        conflicts = []

        # 1. Room conflict (same weekday, overlapping time)
        room_query = db.query(ScheduleSlot).filter(
            ScheduleSlot.room_id == room_id,
            ScheduleSlot.weekday == weekday,
            ScheduleSlot.start_time < end_time,
            ScheduleSlot.end_time > start_time,
        )
        if exclude_slot_id:
            room_query = room_query.filter(ScheduleSlot.id != exclude_slot_id)
        room_clash = room_query.first()
        if room_clash:
            conflicts.append(
                ConflictItem(
                    type="room",
                    entity_id=room_id,
                    description=f"Room already booked by group #{room_clash.group_id} ({room_clash.start_time} - {room_clash.end_time}).",
                )
            )

        # 2. Teacher conflict
        teacher_query = db.query(ScheduleSlot).filter(
            ScheduleSlot.teacher_id == teacher_id,
            ScheduleSlot.weekday == weekday,
            ScheduleSlot.start_time < end_time,
            ScheduleSlot.end_time > start_time,
        )
        if exclude_slot_id:
            teacher_query = teacher_query.filter(ScheduleSlot.id != exclude_slot_id)
        teacher_clash = teacher_query.first()
        if teacher_clash:
            conflicts.append(
                ConflictItem(
                    type="teacher",
                    entity_id=teacher_id,
                    description=f"Teacher already assigned to group #{teacher_clash.group_id} ({teacher_clash.start_time} - {teacher_clash.end_time}).",
                )
            )

        return conflicts

    @classmethod
    def create_slot(cls, db: Session, data: ScheduleSlotCreate, creator_id: Optional[int] = None) -> ScheduleSlot:
        group = db.query(Group).filter(Group.id == data.group_id).first()
        room = db.query(Room).filter(Room.id == data.room_id).first()
        teacher = db.query(Teacher).filter(Teacher.id == data.teacher_id).first()

        if not group or not room or not teacher:
            raise NotFoundError(message_key="resource_not_found")

        # Check room capacity policy
        policy = cls.get_room_capacity_policy(db, group.branch_id)
        if policy == "block" and room.capacity < group.capacity:
            raise ConflictError(
                message_key="room_capacity_insufficient",
                details={"room_capacity": room.capacity, "group_capacity": group.capacity},
            )

        conflicts = cls.check_slot_conflicts(
            db=db,
            group_id=data.group_id,
            room_id=data.room_id,
            teacher_id=data.teacher_id,
            weekday=data.weekday,
            start_time=data.start_time,
            end_time=data.end_time,
        )
        if conflicts:
            raise ConflictError(
                message_key="conflict_error",
                details=[c.model_dump() for c in conflicts],
            )

        slot = ScheduleSlot(**data.model_dump())
        db.add(slot)
        db.commit()
        db.refresh(slot)
        return slot

    @classmethod
    def is_closure_date(cls, db: Session, target_date: date, branch_id: int) -> Optional[ClosureDay]:
        return (
            db.query(ClosureDay)
            .filter(
                (ClosureDay.branch_id == branch_id) | (ClosureDay.branch_id.is_(None)),
                ClosureDay.start_date <= target_date,
                ClosureDay.end_date >= target_date,
            )
            .first()
        )

    @classmethod
    def generate_sessions(
        cls, db: Session, group_id: int, start_date: date, end_date: date, creator_id: Optional[int] = None
    ) -> GenerateSessionsResponse:
        """Generate concrete class sessions from weekly slots, skipping registered closure days."""
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise NotFoundError(message_key="group_not_found")

        slots = db.query(ScheduleSlot).filter(ScheduleSlot.group_id == group_id).all()
        if not slots:
            raise BadRequestError(message_key="validation_error", details="Group has no weekly schedule slots defined.")

        generated_count = 0
        skipped_dates = []

        curr = start_date
        while curr <= end_date:
            weekday = curr.weekday()  # 0=Monday .. 6=Sunday
            matching_slots = [s for s in slots if s.weekday == weekday]

            if matching_slots:
                # Check closure days
                closure = cls.is_closure_date(db, curr, group.branch_id)
                if closure:
                    skipped_dates.append(curr)
                else:
                    for s in matching_slots:
                        # Check if session already generated for this group, date and start_time
                        exists = (
                            db.query(ClassSession)
                            .filter(
                                ClassSession.group_id == group_id,
                                ClassSession.session_date == curr,
                                ClassSession.start_time == s.start_time,
                            )
                            .first()
                        )
                        if not exists:
                            session = ClassSession(
                                group_id=group_id,
                                room_id=s.room_id,
                                teacher_id=s.teacher_id,
                                session_date=curr,
                                start_time=s.start_time,
                                end_time=s.end_time,
                                status="planned",
                            )
                            db.add(session)
                            generated_count += 1
            curr += timedelta(days=1)

        db.commit()
        return GenerateSessionsResponse(generated_count=generated_count, skipped_dates=skipped_dates)

    @classmethod
    def cancel_session(
        cls, db: Session, session_id: int, reason: str, canceller_id: int, ip_address: Optional[str] = None
    ) -> ClassSession:
        session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
        if not session:
            raise NotFoundError(message_key="resource_not_found")

        if session.status == "held":
            raise ConflictError(message_key="session_already_held")

        now = datetime.now(timezone.utc)
        session.status = "cancelled"
        session.cancel_reason = reason
        session.cancelled_by = canceller_id
        session.cancelled_at = now

        # Notify teacher, group students and their parents
        recipients = []
        if session.teacher and session.teacher.user_id:
            recipients.append(session.teacher.user_id)

        enrollments = db.query(Enrollment).filter(Enrollment.group_id == session.group_id, Enrollment.status == "confirmed").all()
        student_ids = [e.student_id for e in enrollments]

        # Student user accounts
        for e in enrollments:
            if e.student and e.student.user_id:
                recipients.append(e.student.user_id)

        # Parent accounts
        if student_ids:
            parents = (
                db.query(StudentParent)
                .filter(StudentParent.student_id.in_(student_ids), StudentParent.is_validated.is_(True))
                .all()
            )
            for p in parents:
                if p.parent and p.parent.user_id:
                    recipients.append(p.parent.user_id)

        notification_service.notify_multiple_users(
            db=db,
            user_ids=recipients,
            notif_type="session_cancelled",
            title="Session Cancelled",
            body=f"Session on {session.session_date} ({session.start_time} - {session.end_time}) was cancelled: {reason}",
            data={"session_id": session.id, "reason": reason},
        )

        audit_service.log(
            db=db,
            action="cancel_session",
            entity="ClassSession",
            entity_id=session.id,
            user_id=canceller_id,
            after_json={"status": "cancelled", "reason": reason},
            ip_address=ip_address,
        )

        db.commit()
        db.refresh(session)
        return session

    @classmethod
    def reschedule_session(
        cls, db: Session, session_id: int, data: RescheduleSessionRequest, actor_id: int, ip_address: Optional[str] = None
    ) -> ClassSession:
        old_session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
        if not old_session:
            raise NotFoundError(message_key="resource_not_found")

        if old_session.status == "held":
            raise ConflictError(message_key="session_already_held")

        group = old_session.group
        # Check closure day for new date
        closure = cls.is_closure_date(db, data.new_date, group.branch_id)
        if closure:
            raise ConflictError(message_key="closure_day_conflict", details={"closure_name": closure.name_en})

        target_room_id = data.new_room_id or old_session.room_id
        target_teacher_id = data.new_teacher_id or old_session.teacher_id

        # Check concrete room / teacher conflict on new session date
        room_clash = (
            db.query(ClassSession)
            .filter(
                ClassSession.room_id == target_room_id,
                ClassSession.session_date == data.new_date,
                ClassSession.status.in_(["planned", "held"]),
                ClassSession.start_time < data.new_end_time,
                ClassSession.end_time > data.new_start_time,
            )
            .first()
        )
        if room_clash:
            raise ConflictError(message_key="room_schedule_conflict")

        teacher_clash = (
            db.query(ClassSession)
            .filter(
                ClassSession.teacher_id == target_teacher_id,
                ClassSession.session_date == data.new_date,
                ClassSession.status.in_(["planned", "held"]),
                ClassSession.start_time < data.new_end_time,
                ClassSession.end_time > data.new_start_time,
            )
            .first()
        )
        if teacher_clash:
            raise ConflictError(message_key="teacher_schedule_conflict")

        # Mark old session as rescheduled
        old_session.status = "rescheduled"
        old_session.cancel_reason = f"Rescheduled to {data.new_date}: {data.reason}"

        # Create new session linked
        new_session = ClassSession(
            group_id=old_session.group_id,
            room_id=target_room_id,
            teacher_id=target_teacher_id,
            session_date=data.new_date,
            start_time=data.new_start_time,
            end_time=data.new_end_time,
            status="planned",
            rescheduled_from_session_id=old_session.id,
        )
        db.add(new_session)
        db.flush()

        audit_service.log(
            db=db,
            action="reschedule_session",
            entity="ClassSession",
            entity_id=old_session.id,
            user_id=actor_id,
            after_json={"rescheduled_to_id": new_session.id, "new_date": str(data.new_date), "reason": data.reason},
            ip_address=ip_address,
        )

        db.commit()
        db.refresh(new_session)
        return new_session

    @classmethod
    def apply_closure_day(cls, db: Session, closure: ClosureDay, actor_id: Optional[int] = None) -> int:
        """Cancel existing planned sessions that fall on the newly created/extended closure day."""
        query = db.query(ClassSession).filter(
            ClassSession.session_date >= closure.start_date,
            ClassSession.session_date <= closure.end_date,
            ClassSession.status == "planned",
        )
        if closure.branch_id is not None:
            query = query.join(Group).filter(Group.branch_id == closure.branch_id)

        affected_sessions = query.all()
        count = len(affected_sessions)
        for s in affected_sessions:
            cls.cancel_session(
                db=db,
                session_id=s.id,
                reason=f"School closure: {closure.name_en}",
                canceller_id=actor_id or 1,
            )
        return count


schedule_service = ScheduleService()

