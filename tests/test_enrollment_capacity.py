from datetime import datetime, timedelta, timezone
from decimal import Decimal
from tests.conftest import make_auth_headers
from app.models.student import Student
from app.models.enrollment import Enrollment


def test_enrollment_capacity_and_overbooking(client, db, seed_data):
    agent_headers = make_auth_headers(seed_data["agent"])
    dir_headers = make_auth_headers(seed_data["director"])
    group = seed_data["group"]  # capacity = 2

    # Create 2 students
    s1 = Student(branch_id=seed_data["branch1"].id, student_number="STD-TEST-001", first_name="Ali", last_name="Benaissa", status="candidate")
    s2 = Student(branch_id=seed_data["branch1"].id, student_number="STD-TEST-002", first_name="Sara", last_name="Mansouri", status="candidate")
    s3 = Student(branch_id=seed_data["branch1"].id, student_number="STD-TEST-003", first_name="Omar", last_name="Kaddour", status="candidate")
    db.add_all([s1, s2, s3])
    db.commit()

    # 1. Booking spot 1
    res1 = client.post(
        "/api/v1/enrollments",
        headers=agent_headers,
        json={
            "student_id": s1.id,
            "group_id": group.id,
            "branch_id": group.branch_id,
            "total_fee": 15000.00,
        },
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "pending_payment"

    # 2. Booking spot 2 (now group is full: 2/2)
    res2 = client.post(
        "/api/v1/enrollments",
        headers=agent_headers,
        json={
            "student_id": s2.id,
            "group_id": group.id,
            "branch_id": group.branch_id,
            "total_fee": 15000.00,
        },
    )
    assert res2.status_code == 200

    # 3. Booking spot 3 by Agent -> must fail with 409 group_capacity_exceeded!
    res3 = client.post(
        "/api/v1/enrollments",
        headers=agent_headers,
        json={
            "student_id": s3.id,
            "group_id": group.id,
            "branch_id": group.branch_id,
            "total_fee": 15000.00,
        },
    )
    assert res3.status_code == 409
    assert res3.json()["code"] == "CONFLICT"

    # 4. Agent attempts over-capacity -> Forbidden (403)!
    res_agent_over = client.post(
        "/api/v1/enrollments",
        headers=agent_headers,
        json={
            "student_id": s3.id,
            "group_id": group.id,
            "branch_id": group.branch_id,
            "total_fee": 15000.00,
            "allow_over_capacity": True,
            "over_capacity_reason": "Special case",
        },
    )
    assert res_agent_over.status_code == 403

    # 5. Director attempts over-capacity with reason -> Allowed (200)!
    res_dir_over = client.post(
        "/api/v1/enrollments",
        headers=dir_headers,
        json={
            "student_id": s3.id,
            "group_id": group.id,
            "branch_id": group.branch_id,
            "total_fee": 15000.00,
            "allow_over_capacity": True,
            "over_capacity_reason": "Director authorization",
        },
    )
    assert res_dir_over.status_code == 200


def test_capacity_reduction_refused_if_occupied(client, db, seed_data):
    dir_headers = make_auth_headers(seed_data["director"])
    group = seed_data["group"]

    # First enroll 2 students so 2 spots are occupied
    s1 = Student(branch_id=seed_data["branch1"].id, student_number="STD-RED-01", first_name="A", last_name="B")
    s2 = Student(branch_id=seed_data["branch1"].id, student_number="STD-RED-02", first_name="C", last_name="D")
    db.add_all([s1, s2])
    db.flush()

    enr1 = Enrollment(reference="ENR-RED-01", student_id=s1.id, group_id=group.id, branch_id=group.branch_id, status="confirmed")
    enr2 = Enrollment(reference="ENR-RED-02", student_id=s2.id, group_id=group.id, branch_id=group.branch_id, status="confirmed")
    db.add_all([enr1, enr2])
    db.commit()

    # Try to reduce capacity to 1 when occupied is 2 -> 409 Conflict!
    res = client.patch(
        f"/api/v1/groups/{group.id}/capacity",
        headers=dir_headers,
        json={"capacity": 1},
    )
    assert res.status_code == 409


def test_confirm_enrollment_minimum_deposit(client, db, seed_data):
    agent_headers = make_auth_headers(seed_data["agent"])
    group = seed_data["group"]

    student = Student(branch_id=seed_data["branch1"].id, student_number="STD-DEP-01", first_name="Karim", last_name="Saadi")
    db.add(student)
    db.commit()

    # Create reservation
    enr = Enrollment(
        reference="ENR-DEP-TEST",
        student_id=student.id,
        group_id=group.id,
        branch_id=group.branch_id,
        status="pending_payment",
        total_fee=Decimal("15000.00"),
        reserved_until=datetime.now(timezone.utc) + timedelta(days=2),
    )
    db.add(enr)
    db.commit()

    # Try to confirm with deposit below minimum (e.g. 500 DA when min is 2000 DA) -> 400
    res_fail = client.post(
        f"/api/v1/enrollments/{enr.id}/confirm",
        headers=agent_headers,
        json={"initial_payment_amount": 500.00, "payment_method": "cash"},
    )
    assert res_fail.status_code == 400

    # Confirm with valid deposit (2500 DA >= 2000 DA) -> 200 Confirmed!
    res_ok = client.post(
        f"/api/v1/enrollments/{enr.id}/confirm",
        headers=agent_headers,
        json={"initial_payment_amount": 2500.00, "payment_method": "cash"},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "confirmed"
