from typing import List, Optional
from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.branch import Branch
from app.models.contact_message import ContactMessage
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.group import Group
from app.schemas.announcement import AnnouncementResponse
from app.schemas.branch import BranchResponse
from app.schemas.common import StatusResponse
from app.schemas.contact_message import ContactMessageCreate, ContactMessageResponse
from app.schemas.course import CourseResponse
from app.schemas.document import DocumentResponse
from app.schemas.enrollment import EnrollmentResponse, PublicPreregistrationRequest
from app.schemas.group import GroupAvailabilityResponse
from app.schemas.otp import OtpStatusResponse, SendOtpRequest, VerifyOtpRequest
from app.services.document_service import document_service
from app.services.enrollment_service import enrollment_service
from app.services.otp_service import otp_service

router = APIRouter(prefix="/public", tags=["Public Portal"])


@router.get("/branches", response_model=List[BranchResponse])
def get_public_branches(db: Session = Depends(get_db)):
    return db.query(Branch).filter(Branch.is_active.is_(True), Branch.is_archived.is_(False)).all()


@router.get("/courses", response_model=List[CourseResponse])
def get_public_courses(
    branch_id: Optional[int] = None,
    course_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Course).filter(Course.is_published.is_(True), Course.is_archived.is_(False))
    if branch_id:
        query = query.filter(Course.branch_id == branch_id)
    if course_type:
        query = query.filter(Course.type == course_type)
    return query.all()


@router.get("/groups", response_model=List[GroupAvailabilityResponse])
def get_public_groups(branch_id: Optional[int] = None, level_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Group).filter(Group.status.in_(["upcoming", "active"]), Group.is_archived.is_(False))
    if branch_id:
        query = query.filter(Group.branch_id == branch_id)
    if level_id:
        query = query.filter(Group.level_id == level_id)

    groups = query.all()
    results = []
    for g in groups:
        cap = enrollment_service.get_effective_capacity(db, g)
        conf, res, occupied = enrollment_service.get_occupied_spots(db, g.id)
        avail = max(0, cap - occupied)
        results.append(
            GroupAvailabilityResponse(
                group_id=g.id,
                group_name=g.name,
                total_capacity=cap,
                confirmed_enrollments=conf,
                active_reservations=res,
                available_spots=avail,
                is_full=(avail == 0),
            )
        )
    return results


@router.get("/announcements", response_model=List[AnnouncementResponse])
def get_public_announcements(branch_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Announcement).filter(
        Announcement.is_public.is_(True),
        Announcement.is_archived.is_(False),
    )
    if branch_id:
        query = query.filter((Announcement.branch_id == branch_id) | (Announcement.branch_id.is_(None)))
    return query.order_by(Announcement.published_at.desc()).limit(20).all()


@router.post("/contact", response_model=ContactMessageResponse)
def submit_contact_form(data: ContactMessageCreate, db: Session = Depends(get_db)):
    msg = ContactMessage(**data.model_dump())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.post("/preregistrations", response_model=EnrollmentResponse)
def public_preregistration(data: PublicPreregistrationRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    return enrollment_service.public_preregistration(db, data, ip_address=ip)


@router.post("/preregistrations/{id}/documents", response_model=DocumentResponse)
def upload_preregistration_document(
    id: int,
    file: UploadFile = File(...),
    kind: str = "registration",
    db: Session = Depends(get_db),
):
    enr = db.query(Enrollment).filter(Enrollment.id == id).first()
    if not enr:
        raise NotFoundError(message_key="enrollment_not_found")
    return document_service.upload_document(
        db=db,
        upload_file=file,
        owner_type="enrollment",
        owner_id=enr.id,
        kind=kind,
        visibility="internal",
    )


@router.get("/preregistrations/{reference}", response_model=EnrollmentResponse)
def track_preregistration_status(reference: str, db: Session = Depends(get_db)):
    enr = db.query(Enrollment).filter(Enrollment.reference == reference.strip()).first()
    if not enr:
        raise NotFoundError(message_key="enrollment_not_found")
    return enr


@router.post("/otp/send", response_model=OtpStatusResponse)
def send_otp_code(data: SendOtpRequest, db: Session = Depends(get_db)):
    """Envoie un code de confirmation à 6 chiffres par email via Brevo."""
    otp_service.send_otp(db, email=data.email, purpose=data.purpose or "preregistration")
    return OtpStatusResponse(
        code="SUCCESS",
        message="Code de vérification envoyé avec succès à votre adresse email.",
        email=data.email,
        is_verified=False,
    )


@router.post("/otp/verify", response_model=OtpStatusResponse)
def verify_otp_code(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    """Vérifie la validité du code OTP saisi par l'élève."""
    otp_service.verify_otp(db, email=data.email, otp_code=data.otp_code, purpose=data.purpose or "preregistration")
    return OtpStatusResponse(
        code="SUCCESS",
        message="Adresse email confirmée avec succès.",
        email=data.email,
        is_verified=True,
    )


