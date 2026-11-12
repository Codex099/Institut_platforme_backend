import pytest
from app.models.otp import EmailVerification
from app.models.student import Student


def test_send_and_verify_otp(client, db):
    email = "candidat.test@gmail.com"

    # 1. Demande d'envoi du code OTP
    response = client.post("/api/v1/public/otp/send", json={"email": email, "purpose": "preregistration"})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "SUCCESS"
    assert data["email"] == email
    assert data["is_verified"] is False

    # Récupérer le code généré en base
    record = db.query(EmailVerification).filter(EmailVerification.email == email).first()
    assert record is not None
    assert len(record.otp_code) == 6
    assert record.is_verified is False

    # 2. Test avec un mauvais code OTP (doit échouer)
    bad_resp = client.post("/api/v1/public/otp/verify", json={"email": email, "otp_code": "000000"})
    assert bad_resp.status_code == 400
    db.refresh(record)
    assert record.attempts == 1

    # 3. Test avec le bon code OTP (doit réussir)
    good_resp = client.post("/api/v1/public/otp/verify", json={"email": email, "otp_code": record.otp_code})
    assert good_resp.status_code == 200
    assert good_resp.json()["is_verified"] is True

    db.refresh(record)
    assert record.is_verified is True
    assert record.verified_at is not None


def test_preregistration_blocked_without_otp(client, seed_data):
    # Tentative de préinscription sans avoir validé l'email par OTP -> Doit renvoyer 400
    branch = seed_data["branch1"]
    group = seed_data["group"]
    payload = {
        "branch_id": branch.id,
        "group_id": group.id,
        "first_name": "Yacine",
        "last_name": "Belkacem",
        "phone": "0559998877",
        "email": "unverified.student@gmail.com",
    }
    resp = client.post("/api/v1/public/preregistrations", json=payload)
    assert resp.status_code == 400
    err = resp.json()
    assert "OTP" in str(err) or "validation_error" in str(err)


def test_preregistration_succeeds_after_otp(client, db, seed_data):
    branch = seed_data["branch1"]
    group = seed_data["group"]
    email = "verified.student@gmail.com"

    # 1. Envoi OTP
    client.post("/api/v1/public/otp/send", json={"email": email})
    record = db.query(EmailVerification).filter(EmailVerification.email == email).first()

    # 2. Validation OTP
    verify_resp = client.post("/api/v1/public/otp/verify", json={"email": email, "otp_code": record.otp_code})
    assert verify_resp.status_code == 200

    # 3. Préinscription autorisée
    payload = {
        "branch_id": branch.id,
        "group_id": group.id,
        "first_name": "Amina",
        "last_name": "Mansouri",
        "phone": "0551112233",
        "email": email,
    }
    resp = client.post("/api/v1/public/preregistrations", json=payload)
    assert resp.status_code == 200
    enr_data = resp.json()
    assert enr_data["status"] == "pending_payment"
    assert enr_data["source"] == "online"

    # Vérifier que l'étudiant a été créé avec son email
    student = db.query(Student).filter(Student.id == enr_data["student_id"]).first()
    assert student is not None
    assert student.email == email
    assert student.status == "candidate"

