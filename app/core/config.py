import json
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Spécification stricte des variables d'environnement.
    
    Toutes les valeurs réelles sont obligatoirement lues depuis le fichier .env.
    Aucune valeur sensible, mot de passe, adresse ou identifiant n'est codé en dur ici.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Serveur HTTP
    SERVER_HOST: str
    SERVER_PORT: int

    # Base de données
    DATABASE_URL: str

    # Sécurité & Tokens JWT
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Compte Administrateur Initial
    INITIAL_ADMIN_EMAIL: str
    INITIAL_ADMIN_PASSWORD: str
    INITIAL_ADMIN_FULL_NAME: str
    INITIAL_ADMIN_PHONE: str

    # Branche Siège par défaut
    DEFAULT_BRANCH_NAME: str
    DEFAULT_BRANCH_CODE: str
    DEFAULT_BRANCH_CITY: str
    DEFAULT_BRANCH_ADDRESS: str
    DEFAULT_BRANCH_PHONE: str
    DEFAULT_BRANCH_EMAIL: str

    # Paramètres Métier
    DEFAULT_RESERVATION_HOURS: int
    DEFAULT_DEPOSIT_MIN: float
    DEFAULT_GROUP_CAPACITY: int
    ATTENDANCE_EDIT_WINDOW_HOURS: int
    ROOM_CAPACITY_POLICY: str

    # Stockage
    STORAGE_BACKEND: str
    STORAGE_LOCAL_DIR: str
    S3_ENDPOINT_URL: Optional[str] = ""
    S3_ACCESS_KEY: Optional[str] = ""
    S3_SECRET_KEY: Optional[str] = ""
    S3_BUCKET_NAME: Optional[str] = ""
    S3_REGION: Optional[str] = ""

    # Brevo API (Email & OTP)
    BREVO_API_KEY: Optional[str] = ""
    BREVO_API_URL: str
    BREVO_SENDER_EMAIL: str
    BREVO_SENDER_NAME: str
    OTP_EXPIRE_MINUTES: int
    OTP_COOLDOWN_SECONDS: int
    OTP_MAX_ATTEMPTS: int

    # URL du Frontend (pour les boutons et liens dans les emails)
    FRONTEND_URL: str = "http://localhost:3000"

    # Réseau & Limitation de débit
    CORS_ORIGINS: Union[List[str], str] = ["*"]
    MAX_UPLOAD_SIZE_MB: int
    RATE_LIMIT_LOGIN_PER_MINUTE: int
    RATE_LIMIT_PUBLIC_PER_MINUTE: int

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            try:
                return json.loads(v)
            except Exception:
                return ["*"]
        elif isinstance(v, list):
            return v
        return ["*"]


settings = Settings()
