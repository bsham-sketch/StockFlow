import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def _secret_key() -> str:
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY must be configured in the environment.")
    return secret


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(user_id: int, organization_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    claims = {
        "user_id": user_id,
        "organization_id": organization_id,
        "exp": expires_at,
    }
    return jwt.encode(claims, _secret_key(), algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        claims = jwt.decode(credentials.credentials, _secret_key(), algorithms=[ALGORITHM])
        user_id = int(claims["user_id"])
        organization_id = int(claims["organization_id"])
    except (JWTError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    user = (
        db.query(User)
        .filter(User.id == user_id, User.organization_id == organization_id)
        .first()
    )
    if user is None:
        raise unauthorized
    return user
