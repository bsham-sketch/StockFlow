from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Organization, User
from app.schemas import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_organization(db: Session, organization_id: int) -> Organization:
    return db.query(Organization).filter(Organization.id == organization_id).one()


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Organization:
    return _get_organization(db, user.organization_id)


@router.put("", response_model=SettingsResponse)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Organization:
    organization = _get_organization(db, user.organization_id)
    organization.default_low_stock_threshold = payload.default_low_stock_threshold
    db.commit()
    db.refresh(organization)
    return organization
