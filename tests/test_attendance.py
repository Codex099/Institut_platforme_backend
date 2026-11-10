from datetime import date, time, timedelta
from tests.conftest import make_auth_headers
from app.models.attendance import Attendance
from app.models.enrollment import Enrollment
from app.models.session import ClassSession
from app.models.student import Student


def test_teacher_strictly_forbidden_from_finances(client, seed_data):
    teacher_headers = make_auth_headers(seed_data["teacher"])

    # 1. Teacher attempts to view payments -> 403 Forbidden!
    res_pay = client.get("/api/v1/payments", headers=teacher_headers)
    assert res_pay.status_code == 403

    # 2. Teacher attempts to view cash registers -> 403 Forbidden!
    res_cash = client.get("/api/v1/cash-registers", headers=teacher_headers)
    assert res_cash.status_code == 403

    # 3. Teacher attempts to access payroll -> 403 Forbidden!
    res_payroll = client.get("/api/v1/payroll", headers=teacher_headers)
    assert res_payroll.status_code == 403


def test_manual_attendance_flow(client, db, seed_data):
    teacher_headers = make_auth_headers(seed_data["teacher"])
    group = seed_data["group"]
    room = seed_data["room"]
    teacher = seed_data["teacher_profile"]

    # Student enrolled in group
    student = Student(branch_id=seed_data["branch1"].id, student_number="STD-ATT-01", first_name="Bilal", last_name="Mahi")
    db.add(student)
    db.flush()

    enr = Enrollment(
        reference="ENR-ATT-01",
        student_id=student.id,
        group_id=group.id,
        branch_id=group.branch_id,
        status="confirmed",
    )
    db.add(enr)

    # Session today
    session = ClassSession(
        group_id=group.id,
        room_id=room.id,
        teacher_id=teacher.id,
        session_date=date.today(),
        start_time=time(9, 0),
        end_time=time(11, 0),
        status="planned",
    )
    db.add(session)
    db.commit()

    # Teacher records attendance
    res = client.post(
        "/api/v1/attendance/manual",
        headers=teacher_headers,
        json={
            "session_id": session.id,
            "records": [{"student_id": student.id, "status": "present", "notes": "On time"}],
        },
    )
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["status"] == "present"

    # Anti-doublon check: re-submitting updates the existing record
    res2 = client.post(
        "/api/v1/attendance/manual",
        headers=teacher_headers,
        json={
            "session_id": session.id,
            "records": [{"student_id": student.id, "status": "late", "notes": "Arrived 15m late"}],
        },
    )
    assert res2.status_code == 200
    assert res2.json()[0]["status"] == "late"

    # Check only 1 record exists in DB for (session_id, student_id)
    count = db.query(Attendance).filter(Attendance.session_id == session.id, Attendance.student_id == student.id).count()
    assert count == 1


def test_cancelled_session_rejects_attendance(client, db, seed_data):
    teacher_headers = make_auth_headers(seed_data["teacher"])
    group = seed_data["group"]
    room = seed_data["room"]
    teacher = seed_data["teacher_profile"]

    session = ClassSession(
        group_id=group.id,
        room_id=room.id,
        teacher_id=teacher.id,
        session_date=date.today(),
        start_time=time(9, 0),
        end_time=time(11, 0),
        status="cancelled",
        cancel_reason="Holiday",
    )
    db.add(session)
    db.commit()

    res = client.post(
        "/api/v1/attendance/manual",
        headers=teacher_headers,
        json={
            "session_id": session.id,
            "records": [{"student_id": 1, "status": "present"}],
        },
    )
    assert res.status_code == 400

