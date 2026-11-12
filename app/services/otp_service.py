import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.models.otp import EmailVerification
from app.services.email_service import email_service


class OtpService:
    @staticmethod
    def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @classmethod
    def send_otp(cls, db: Session, email: str, purpose: str = "preregistration") -> None:
        """Génère et envoie un code de confirmation à 6 chiffres par email."""
        clean_email = email.lower().strip()
        now = datetime.now(timezone.utc)

        # Recherche d'un enregistrement existant
        record = (
            db.query(EmailVerification)
            .filter(
                EmailVerification.email == clean_email,
                EmailVerification.purpose == purpose,
            )
            .first()
        )

        # Anti-spam : empêcher l'envoi de plusieurs codes en moins de OTP_COOLDOWN_SECONDS
        if record and record.created_at:
            created_at = cls._ensure_utc(record.created_at)
            if (now - created_at).total_seconds() < settings.OTP_COOLDOWN_SECONDS:
                raise BadRequestError(
                    message_key="validation_error",
                    details=f"Veuillez patienter {settings.OTP_COOLDOWN_SECONDS} secondes avant de demander un nouveau code.",
                )

        # Générer un code à 6 chiffres
        otp_code = f"{secrets.randbelow(900000) + 100000}"
        expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        if record:
            record.otp_code = otp_code
            record.expires_at = expires_at
            record.attempts = 0
            record.is_verified = False
            record.created_at = now
        else:
            record = EmailVerification(
                email=clean_email,
                otp_code=otp_code,
                purpose=purpose,
                is_verified=False,
                expires_at=expires_at,
                attempts=0,
                created_at=now,
            )
            db.add(record)

        db.commit()

        # Envoi via l'API Brevo
        email_service.send_otp_email(to_email=clean_email, otp_code=otp_code)

    @classmethod
    def verify_otp(cls, db: Session, email: str, otp_code: str, purpose: str = "preregistration") -> bool:
        """Vérifie le code OTP saisi par l'élève."""
        clean_email = email.lower().strip()
        now = datetime.now(timezone.utc)

        record = (
            db.query(EmailVerification)
            .filter(
                EmailVerification.email == clean_email,
                EmailVerification.purpose == purpose,
            )
            .first()
        )

        if not record:
            raise BadRequestError(
                message_key="validation_error",
                details="Aucun code de confirmation n'a été demandé pour cette adresse email.",
            )

        # Sécurité : Bloquer après le nombre maximal de tentatives
        if record.attempts >= settings.OTP_MAX_ATTEMPTS:
            raise BadRequestError(
                message_key="validation_error",
                details="Nombre maximal de tentatives dépassé. Veuillez demander un nouveau code.",
            )

        # Vérifier expiration
        expires_at = cls._ensure_utc(record.expires_at)
        if expires_at and expires_at < now:
            raise BadRequestError(
                message_key="validation_error",
                details="Le code de confirmation a expiré. Veuillez en demander un nouveau.",
            )

        # Vérifier la correspondance du code
        if record.otp_code.strip() != otp_code.strip():
            record.attempts += 1
            db.commit()
            remaining = max(0, settings.OTP_MAX_ATTEMPTS - record.attempts)
            raise BadRequestError(
                message_key="validation_error",
                details=f"Code de confirmation incorrect ({remaining} tentative(s) restante(s)).",
            )

        # Code validé avec succès
        record.is_verified = True
        record.verified_at = now
        db.commit()
        return True

    @classmethod
    def is_email_verified(
        cls, db: Session, email: str, purpose: str = "preregistration", max_age_minutes: int = 60
    ) -> bool:
        """Vérifie si l'adresse email a bien été validée par OTP récemment (dans les 60 dernières minutes)."""
        clean_email = email.lower().strip()
        now = datetime.now(timezone.utc)

        record = (
            db.query(EmailVerification)
            .filter(
                EmailVerification.email == clean_email,
                EmailVerification.purpose == purpose,
                EmailVerification.is_verified.is_(True),
            )
            .first()
        )

        if not record or not record.verified_at:
            return False

        verified_at = cls._ensure_utc(record.verified_at)
        if (now - verified_at).total_seconds() > (max_age_minutes * 60):
            return False

        return True

    @classmethod
    def consume_verification(cls, db: Session, email: str, purpose: str = "preregistration") -> None:
        """Consomme la confirmation d'email pour éviter qu'elle soit réutilisée."""
        clean_email = email.lower().strip()
        db.query(EmailVerification).filter(
            EmailVerification.email == clean_email,
            EmailVerification.purpose == purpose,
        ).delete()
        db.commit()


otp_service = OtpService()

