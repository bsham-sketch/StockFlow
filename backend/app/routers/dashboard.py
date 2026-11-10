from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.inventory import get_stock_status
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

    products = (
        db.query(Product)
        .filter(Product.organization_id == user.organization_id)
        .order_by(Product.quantity_on_hand.asc(), Product.name.asc())
        .all()
    )
    low_stock_items = []
    for product in products:
        threshold, stock_status = get_stock_status(
            product, organization.default_low_stock_threshold
        )
        if stock_status != "In stock":
            low_stock_items.append(
                LowStockItem(
                    name=product.name,
                    sku=product.sku,
                    quantity_on_hand=product.quantity_on_hand,
                    threshold=threshold,
                )
            )
    return DashboardResponse(
        total_products=summary[0],
        total_quantity=summary[1],
        low_stock_items=low_stock_items,
    )
