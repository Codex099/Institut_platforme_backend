import logging
import os
from pathlib import Path
from typing import Optional
import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialisation du moteur de templates Jinja2
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailService:
    @property
    def api_url(self) -> str:
        return settings.BREVO_API_URL

    @classmethod
    def render_otp_template(cls, to_email: str, otp_code: str, to_name: Optional[str] = None) -> str:
        """Génère le contenu HTML de l'email à partir du fichier template app/templates/emails/otp_verification.html."""
        template_name = "otp_verification.html"
        verification_link = ""
        if settings.FRONTEND_URL:
            verification_link = f"{settings.FRONTEND_URL.rstrip('/')}/verify-otp?email={to_email}&code={otp_code}"

        context = {
            "school_name": settings.BREVO_SENDER_NAME,
            "student_name": to_name or "Chèr(e) élève",
            "otp_code": otp_code,
            "expire_minutes": settings.OTP_EXPIRE_MINUTES,
            "verification_link": verification_link,
            "frontend_url": settings.FRONTEND_URL,
        }

        try:
            template = jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.warning("Template %s introuvable (%s), utilisation du gabarit par défaut.", template_name, e)
            return f"<p>Votre code de vérification est : <strong>{otp_code}</strong> (valable {settings.OTP_EXPIRE_MINUTES} minutes).</p>"

    @classmethod
    def send_otp_email(cls, to_email: str, otp_code: str, to_name: Optional[str] = None) -> bool:
        """Envoie un code OTP à l'adresse email spécifiée via l'API Brevo.
        
        En l'absence de clé API configurée (mode dev/test), le code est affiché
        dans la console sans bloquer l'utilisateur.
        """
        subject = f"{otp_code} est votre code de confirmation - {settings.BREVO_SENDER_NAME}"
        html_content = cls.render_otp_template(to_email=to_email, otp_code=otp_code, to_name=to_name)

        # Vérification si la clé API Brevo est configurée
        api_key = settings.BREVO_API_KEY.strip() if settings.BREVO_API_KEY else ""
        if not api_key:
            logger.warning(
                "⚠️ [BREVO NON CONFIGURÉ] Clé BREVO_API_KEY absente dans .env. "
                "Affichage du code OTP pour le développement :"
            )
            print(f"\n" + "=" * 50)
            print(f"  🔑 CODE OTP BREVO (DEV MODE)")
            print(f"  👉 Destinataire : {to_email}")
            print(f"  👉 Code OTP     : {otp_code}")
            print(f"  👉 Validité     : {settings.OTP_EXPIRE_MINUTES} minutes")
            print("=" * 50 + "\n")
            return True

        # Envoi réel via l'API Brevo v3
        payload = {
            "sender": {
                "name": settings.BREVO_SENDER_NAME,
                "email": settings.BREVO_SENDER_EMAIL,
            },
            "to": [
                {
                    "email": to_email,
                    "name": to_name or to_email,
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
        }

        headers = {
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(settings.BREVO_API_URL, json=payload, headers=headers)
                if response.status_code in (200, 201, 202):
                    logger.info("✅ Email OTP envoyé avec succès via Brevo à %s", to_email)
                    return True
                else:
                    logger.error("❌ Échec envoi email Brevo (%s): %s", response.status_code, response.text)
                    return False
        except Exception as e:
            logger.error("❌ Exception lors de l'appel Brevo API : %s", e)
            return False


email_service = EmailService()
