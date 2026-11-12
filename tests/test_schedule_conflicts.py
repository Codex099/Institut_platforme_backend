from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from tests.conftest import make_auth_headers
from app.models.closure_day import ClosureDay
from app.models.group import Group
from app.models.schedule import ScheduleSlot
from app.models.session import ClassSession


def test_schedule_slot_room_conflict(client, seed_data):
    dir_headers = make_auth_headers(seed_data["director"])
    group = seed_data["group"]
    room = seed_data["room"]
    teacher = seed_data["teacher_profile"]

    # Slot 1: Monday 09:00 - 11:00
    res1 = client.post(
        "/api/v1/schedules",
        headers=dir_headers,
        json={
            "group_id": group.id,
            "room_id": room.id,
            "teacher_id": teacher.id,
            "weekday": 0,
            "start_time": "09:00:00",
            "end_time": "11:00:00",
        },
    )
    assert res1.status_code == 200

    # Slot 2: Same room, same day, overlapping 10:00 - 12:00 -> 409 Conflict!
    res2 = client.post(
        "/api/v1/schedules",
        headers=dir_headers,
        json={
            "group_id": group.id,
            "room_id": room.id,
            "teacher_id": teacher.id,
            "weekday": 0,
            "start_time": "10:00:00",
            "end_time": "12:00:00",
        },
    )
    assert res2.status_code == 409


def test_session_generation_skips_closure_days(client, db, seed_data):
    dir_headers = make_auth_headers(seed_data["director"])
    group = seed_data["group"]
    room = seed_data["room"]
    teacher = seed_data["teacher_profile"]

    # Ensure a slot exists on Monday (weekday 0)
    slot = ScheduleSlot(
        group_id=group.id,
        room_id=room.id,
        teacher_id=teacher.id,
        weekday=0,
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    db.add(slot)
    db.commit()

    # Add a closure day for upcoming Monday
    today = date.today()
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_monday = today + timedelta(days=days_ahead)

    closure = ClosureDay(
        branch_id=group.branch_id,
        name_ar="عطلة رسمية",
        name_en="National Holiday",
        start_date=next_monday,
        end_date=next_monday,
    )
    db.add(closure)
    db.commit()

    # Generate sessions
    gen_res = client.post(
        "/api/v1/sessions/generate",
        headers=dir_headers,
        json={
            "group_id": group.id,
            "start_date": str(next_monday),
            "end_date": str(next_monday + timedelta(days=6)),
        },
    )
    assert gen_res.status_code == 200
    data = gen_res.json()
    assert str(next_monday) in data["skipped_dates"]


def test_session_cancellation_and_reschedule(client, db, seed_data):
    dir_headers = make_auth_headers(seed_data["director"])
    group = seed_data["group"]
    room = seed_data["room"]
    teacher = seed_data["teacher_profile"]

    session = ClassSession(
        group_id=group.id,
        room_id=room.id,
        teacher_id=teacher.id,
        session_date=date.today() + timedelta(days=3),
        start_time=time(14, 0),
        end_time=time(16, 0),
        status="planned",
    )
    db.add(session)
    db.commit()

    # Cancel session
    cancel_res = client.post(
        f"/api/v1/sessions/{session.id}/cancel",
        headers=dir_headers,
        json={"reason": "Teacher emergency illness"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Reschedule session
    new_date = date.today() + timedelta(days=5)
    resched_res = client.post(
        f"/api/v1/sessions/{session.id}/reschedule",
        headers=dir_headers,
        json={
            "new_date": str(new_date),
            "new_start_time": "14:00:00",
            "new_end_time": "16:00:00",
            "reason": "Makeup session",
        },
    )
    assert resched_res.status_code == 200
    assert resched_res.json()["status"] == "planned"
    assert resched_res.json()["rescheduled_from_session_id"] == session.id
