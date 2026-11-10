from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError

ph = PasswordHasher()
security_bearer = HTTPBearer(auto_error=False)

# In-memory blacklist for invalidated refresh tokens (logout)
# In production with multiple workers, this can be synced to Redis/DB.
REVOKED_TOKENS: Set[str] = set()


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2 hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def create_access_token(subject: str, role: str, branch_id: Optional[int] = None, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Generate short-lived JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(subject),
        "role": role,
        "branch_id": branch_id,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Generate long-lived JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(subject),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, is_refresh: bool = False) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    secret = settings.JWT_REFRESH_SECRET_KEY if is_refresh else settings.JWT_SECRET_KEY
    expected_type = "refresh" if is_refresh else "access"
    
    if token in REVOKED_TOKENS:
        raise AuthenticationError(message_key="auth_token_invalid")
        
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            raise AuthenticationError(message_key="auth_token_invalid")
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(message_key="auth_token_expired")
    except jwt.PyJWTError:
        raise AuthenticationError(message_key="auth_token_invalid")


def revoke_token(token: str) -> None:
    """Add token to revocation set."""
    REVOKED_TOKENS.add(token)


# We'll import get_db lazily in get_current_user to avoid circular dependencies
def get_current_user_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Dict[str, Any]:
    """Fast dependency to extract and validate JWT claims without querying DB."""
    if not credentials or not credentials.credentials:
        raise AuthenticationError(message_key="auth_invalid_credentials")
    return decode_token(credentials.credentials, is_refresh=False)
