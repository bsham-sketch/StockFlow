from app.models import Product


def get_stock_status(
    product: Product, default_threshold: int
) -> tuple[int, str]:
    threshold = (
        product.low_stock_threshold
        if product.low_stock_threshold is not None
        else default_threshold
    )
    if product.quantity_on_hand == 0:
        return threshold, "Out of stock"
    if product.quantity_on_hand <= threshold:
        return threshold, "Low stock"
    return threshold, "In stock"
