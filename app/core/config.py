import json
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "Plateforme Gestion Écoles"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ecole_chlef_db"

    # Security & JWT
    JWT_SECRET_KEY: str = "dev_super_secret_jwt_key_for_ecole_chlef_2026_secure"
    JWT_REFRESH_SECRET_KEY: str = "dev_super_refresh_secret_jwt_key_for_ecole_chlef_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Business defaults
    DEFAULT_RESERVATION_HOURS: int = 48
    DEFAULT_DEPOSIT_MIN: float = 2000.00
    DEFAULT_GROUP_CAPACITY: int = 15
    ATTENDANCE_EDIT_WINDOW_HOURS: int = 24
    ROOM_CAPACITY_POLICY: str = "warn"  # none | warn | block

    # Storage
    STORAGE_BACKEND: str = "local"  # local | s3
    STORAGE_LOCAL_DIR: str = "./uploads"
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = "ecole-documents"
    S3_REGION: str = "eu-west-1"

    # Network & Rate Limiting
    CORS_ORIGINS: Union[List[str], str] = ["*"]
    MAX_UPLOAD_SIZE_MB: int = 10
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    RATE_LIMIT_PUBLIC_PER_MINUTE: int = 20

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
