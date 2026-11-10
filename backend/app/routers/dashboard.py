from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Organization, Product, User
from app.schemas import DashboardResponse, LowStockItem

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardResponse:
    organization = db.query(Organization).filter(
        Organization.id == user.organization_id
    ).one()
    summary = (
        db.query(
            func.count(Product.id),
            func.coalesce(func.sum(Product.quantity_on_hand), 0),
        )
        .filter(Product.organization_id == user.organization_id)
        .one()
    )

    low_stock_products = (
        db.query(Product)
        .filter(
            Product.organization_id == user.organization_id,
            Product.quantity_on_hand
            <= func.coalesce(
                Product.low_stock_threshold, organization.default_low_stock_threshold
            ),
        )
        .order_by(Product.quantity_on_hand.asc(), Product.name.asc())
        .all()
    )
    return DashboardResponse(
        total_products=summary[0],
        total_quantity=summary[1],
        low_stock_items=[
            LowStockItem(
                name=product.name,
                sku=product.sku,
                quantity_on_hand=product.quantity_on_hand,
                threshold=(
                    product.low_stock_threshold
                    if product.low_stock_threshold is not None
                    else organization.default_low_stock_threshold
                ),
            )
            for product in low_stock_products
        ],
    )
