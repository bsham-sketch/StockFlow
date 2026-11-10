from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.inventory import get_stock_status
from app.models import Product, User
from app.schemas import ProductCreate, ProductResponse, ProductUpdate, StockAdjustment

router = APIRouter(prefix="/api/products", tags=["products"])


def _product_response(product: Product, default_threshold: int) -> ProductResponse:
    response = ProductResponse.model_validate(product)
    effective_threshold, stock_status = get_stock_status(product, default_threshold)
    return response.model_copy(
        update={"effective_threshold": effective_threshold, "status": stock_status}
    )


def _get_product(db: Session, product_id: int, organization_id: int) -> Product:
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.organization_id == organization_id)
        .first()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


def _ensure_unique_sku(
    db: Session, organization_id: int, sku: str, exclude_id: int | None = None
) -> None:
    query = db.query(Product).filter(
        Product.organization_id == organization_id, Product.sku == sku
    )
    if exclude_id is not None:
        query = query.filter(Product.id != exclude_id)
    if query.first():
            raise HTTPException(status_code=409, detail="SKU already exists")


def _duplicate_sku_error() -> HTTPException:
    return HTTPException(status_code=409, detail="SKU already exists")


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductResponse:
    _ensure_unique_sku(db, user.organization_id, payload.sku)
    product = Product(
        **payload.model_dump(),
        organization_id=user.organization_id,
        last_updated_by=user.id,
    )
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _duplicate_sku_error() from None
    db.refresh(product)
    return _product_response(product, user.organization.default_low_stock_threshold)


@router.get("", response_model=list[ProductResponse])
def list_products(
    search: str | None = Query(default=None, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProductResponse]:
    query = db.query(Product).filter(Product.organization_id == user.organization_id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(or_(Product.name.ilike(term), Product.sku.ilike(term)))
    threshold = user.organization.default_low_stock_threshold
    return [
        _product_response(product, threshold)
        for product in query.order_by(Product.name.asc(), Product.id.asc()).all()
    ]


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductResponse:
    product = _get_product(db, product_id, user.organization_id)
    return _product_response(product, user.organization.default_low_stock_threshold)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductResponse:
    product = _get_product(db, product_id, user.organization_id)
    changes = payload.model_dump(exclude_unset=True)
    if "sku" in changes:
        _ensure_unique_sku(db, user.organization_id, changes["sku"], product.id)
    for field, value in changes.items():
        setattr(product, field, value)
    product.last_updated_by = user.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _duplicate_sku_error() from None
    db.refresh(product)
    return _product_response(product, user.organization.default_low_stock_threshold)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    product = _get_product(db, product_id, user.organization_id)
    db.delete(product)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{product_id}/adjust", response_model=ProductResponse)
def adjust_stock(
    product_id: int,
    payload: StockAdjustment,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductResponse:
    product = _get_product(db, product_id, user.organization_id)
    adjusted_quantity = product.quantity_on_hand + payload.delta
    if adjusted_quantity < 0:
        raise HTTPException(
            status_code=422, detail="Stock adjustment cannot make quantity negative."
        )
    product.quantity_on_hand = adjusted_quantity
    product.last_updated_by = user.id
    db.commit()
    db.refresh(product)
    return _product_response(product, user.organization.default_low_stock_threshold)
