from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Product, ProductImage, User
from app.schemas import ProductCreate, ProductResponse, ProductUpdate, StockAdjustment

router = APIRouter(prefix="/api/products", tags=["products"])
MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_SIGNATURES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/gif": lambda data: data.startswith((b"GIF87a", b"GIF89a")),
    "image/webp": lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
}


def _product_response(product: Product, image_present: bool) -> ProductResponse:
    response = ProductResponse.model_validate(product)
    if image_present:
        return response.model_copy(update={"image_url": f"/products/{product.id}/image"})
    return response


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
        raise HTTPException(status_code=409, detail="A product with this SKU already exists.")


def _duplicate_sku_error() -> HTTPException:
    return HTTPException(status_code=409, detail="A product with this SKU already exists.")


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
    return _product_response(product, False)


@router.get("", response_model=list[ProductResponse])
def list_products(
    search: str | None = Query(default=None, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProductResponse]:
    query = (
        db.query(Product, ProductImage.product_id.is_not(None))
        .outerjoin(ProductImage, ProductImage.product_id == Product.id)
        .filter(Product.organization_id == user.organization_id)
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(or_(Product.name.ilike(term), Product.sku.ilike(term)))
    return [
        _product_response(product, image_present)
        for product, image_present in query.order_by(Product.name.asc(), Product.id.asc()).all()
    ]


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductResponse:
    product = _get_product(db, product_id, user.organization_id)
    return _product_response(product, product.image is not None)


@router.put("/{product_id}/image", response_model=ProductResponse)
async def upload_product_image(
    product_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductResponse:
    product = _get_product(db, product_id, user.organization_id)
    content = await image.read(MAX_IMAGE_SIZE + 1)
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Product images must be 5 MB or smaller.")

    content_type = next(
        (kind for kind, matches in IMAGE_SIGNATURES.items() if matches(content)),
        None,
    )
    if content_type is None:
        raise HTTPException(
            status_code=415,
            detail="Use a valid JPEG, PNG, GIF, or WebP image.",
        )

    if product.image is None:
        product.image = ProductImage(content_type=content_type, content=content)
    else:
        product.image.content_type = content_type
        product.image.content = content
    product.last_updated_by = user.id
    db.commit()
    db.refresh(product)
    return _product_response(product, True)


@router.get("/{product_id}/image")
def get_product_image(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    product = _get_product(db, product_id, user.organization_id)
    if product.image is None:
        raise HTTPException(status_code=404, detail="Product image not found.")
    return Response(
        content=product.image.content,
        media_type=product.image.content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{product_id}/image", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_image(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    product = _get_product(db, product_id, user.organization_id)
    if product.image is not None:
        db.delete(product.image)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    return _product_response(product, product.image is not None)


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
    return _product_response(product, product.image is not None)
