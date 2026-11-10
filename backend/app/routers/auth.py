from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import Organization, User
from app.schemas import AuthResponse, LoginRequest, SignupRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id, user.organization_id),
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            organization_id=user.organization_id,
            organization_name=user.organization.name,
        ),
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    organization = Organization(name=payload.organization_name)
    db.add(organization)
    db.flush()
    user = User(
        organization_id=organization.id,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from None
    db.refresh(user)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return _auth_response(user)
