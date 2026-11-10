from app.auth import hash_password
from app.database import SessionLocal, initialize_database
from app.models import Organization, Product, User


DEMO_EMAIL = "demo@stockflow.com"
DEMO_PASSWORD = "Demo@1234"

DEMO_PRODUCTS = [
    {"name": "A5 ruled notebook", "sku": "PAP-001", "quantity_on_hand": 42, "selling_price": 129},
    {"name": "Cotton crew t-shirt", "sku": "APP-014", "quantity_on_hand": 18, "selling_price": 499},
    {"name": "Ceramic coffee mug", "sku": "HOM-008", "quantity_on_hand": 3, "selling_price": 349},
    {"name": "USB-C charging cable", "sku": "ELE-023", "quantity_on_hand": 2, "low_stock_threshold": 4, "selling_price": 299},
    {"name": "Adjustable desk lamp", "sku": "HOM-031", "quantity_on_hand": 0, "selling_price": 1199},
    {"name": "Stainless steel bottle", "sku": "OUT-005", "quantity_on_hand": 27, "selling_price": 799},
    {"name": "Wireless optical mouse", "sku": "ELE-017", "quantity_on_hand": 14, "selling_price": 899},
    {"name": "Reusable canvas tote", "sku": "ACC-011", "quantity_on_hand": 55, "selling_price": 249},
]


def seed_demo_data() -> None:
    initialize_database()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == DEMO_EMAIL).first():
            print("Demo user already exists; seed skipped.")
            return

        organization = Organization(name="StockFlow Demo Store")
        db.add(organization)
        db.flush()
        user = User(
            organization_id=organization.id,
            username="StockFlow Demo",
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        db.flush()
        db.add_all(
            [
                Product(
                    **product,
                    organization_id=organization.id,
                    last_updated_by=user.id,
                )
                for product in DEMO_PRODUCTS
            ]
        )
        db.commit()
        print(f"Created demo account: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
