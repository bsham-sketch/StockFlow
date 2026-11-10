import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-stockflow-only")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.database import Base, get_db, upgrade_product_image_url, upgrade_existing_usernames
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _signup(client: TestClient, email: str, organization_name: str) -> str:
    response = client.post(
        "/api/auth/signup",
        json={
            "username": email.partition("@")[0],
            "email": email,
            "password": "secure-password-123",
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_tenant_isolation_and_sku_uniqueness(client: TestClient):
    token_a = _signup(client, "user-a@example.com", "Organization A")
    token_b = _signup(client, "user-b@example.com", "Organization B")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    product = client.post(
        "/api/products",
        headers=headers_b,
        json={"name": "Private stock", "sku": "SHARED-1", "quantity_on_hand": 12},
    )
    assert product.status_code == 201
    product_id = product.json()["id"]
    duplicate = client.post(
        "/api/products",
        headers=headers_b,
        json={"name": "Duplicate SKU", "sku": "SHARED-1"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "SKU already exists"

    same_sku_other_org = client.post(
        "/api/products",
        headers=headers_a,
        json={"name": "Organization A stock", "sku": "SHARED-1"},
    )
    assert same_sku_other_org.status_code == 201

    assert client.get(f"/api/products/{product_id}", headers=headers_a).status_code == 404
    assert client.put(
        f"/api/products/{product_id}", headers=headers_a, json={"name": "Compromised"}
    ).status_code == 404
    assert client.delete(f"/api/products/{product_id}", headers=headers_a).status_code == 404
    assert client.post(
        f"/api/products/{product_id}/adjust",
        headers=headers_a,
        json={"delta": 1, "note": "Cross tenant attempt"},
    ).status_code == 404
    assert client.get("/api/products", headers=headers_a).json()[0]["name"] == "Organization A stock"
    assert client.get("/api/dashboard", headers=headers_a).json()["total_products"] == 1
    assert client.get("/api/dashboard", headers=headers_b).json()["total_products"] == 1
    settings_a = client.put(
        "/api/settings", headers=headers_a, json={"default_low_stock_threshold": 1}
    )
    assert settings_a.status_code == 200
    assert client.get("/api/settings", headers=headers_b).json()[
        "default_low_stock_threshold"
    ] == 5
    assert client.get(f"/api/products/{product_id}", headers=headers_b).status_code == 200


def test_product_threshold_status_and_stock_adjustments(client: TestClient):
    token = _signup(client, "inventory@example.com", "Inventory Org")
    headers = {"Authorization": f"Bearer {token}"}

    low = client.post(
        "/api/products",
        headers=headers,
        json={"name": "Widget", "sku": "W-1", "quantity_on_hand": 3},
    )
    out = client.post(
        "/api/products",
        headers=headers,
        json={"name": "Empty box", "sku": "W-2", "quantity_on_hand": 0},
    )
    assert low.status_code == out.status_code == 201
    assert low.json()["effective_threshold"] == 5
    assert low.json()["status"] == "Low stock"
    assert out.json()["status"] == "Out of stock"

    dashboard = client.get("/api/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert {item["sku"] for item in dashboard.json()["low_stock_items"]} == {"W-1", "W-2"}
    assert all(item["threshold"] == 5 for item in dashboard.json()["low_stock_items"])

    settings = client.put(
        "/api/settings", headers=headers, json={"default_low_stock_threshold": 2}
    )
    assert settings.status_code == 200
    updated_low = client.get(f"/api/products/{low.json()['id']}", headers=headers)
    assert updated_low.json()["status"] == "In stock"
    assert updated_low.json()["effective_threshold"] == 2

    updated = client.post(
        f"/api/products/{low.json()['id']}/adjust",
        headers=headers,
        json={"delta": -1, "note": "One item sold"},
    )
    assert updated.status_code == 200
    assert updated.json()["quantity_on_hand"] == 2
    assert updated.json()["status"] == "Low stock"
    rejected = client.post(
        f"/api/products/{low.json()['id']}/adjust",
        headers=headers,
        json={"delta": -3, "note": "Would go below zero"},
    )
    assert rejected.status_code == 422


def test_product_validation_and_image_url(client: TestClient):
    token = _signup(client, "validation@example.com", "Validation Org")
    headers = {"Authorization": f"Bearer {token}"}
    invalid = client.post(
        "/api/products",
        headers=headers,
        json={
            "name": "Bad quantity",
            "sku": "BAD-1",
            "quantity_on_hand": -1,
            "image_url": "file:///local/image.png",
        },
    )
    assert invalid.status_code == 422

    created = client.post(
        "/api/products",
        headers=headers,
        json={
            "name": "External Image",
            "sku": "IMG-1",
            "image_url": " https://example.com/image.jpg ",
        },
    )
    assert created.status_code == 201
    assert created.json()["image_url"] == "https://example.com/image.jpg"
    assert client.put(
        f"/api/products/{created.json()['id']}",
        headers=headers,
        json={"quantity_on_hand": None},
    ).status_code == 422
    assert client.post(
        "/api/products",
        headers=headers,
        json={"name": "Bad price", "sku": "BAD-2", "selling_price": -1},
    ).status_code == 422
    assert client.post(
        "/api/products",
        headers=headers,
        json={"name": "Bad threshold", "sku": "BAD-3", "low_stock_threshold": -1},
    ).status_code == 422


def test_existing_databases_receive_image_url_column():
    legacy_engine = create_engine("sqlite://")
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(160) NOT NULL)"
        )
        connection.exec_driver_sql("INSERT INTO products (id, name) VALUES (1, 'Existing')")

    upgrade_product_image_url(legacy_engine)

    with legacy_engine.connect() as connection:
        columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(products)").all()
        }
        name = connection.exec_driver_sql(
            "SELECT name FROM products WHERE id = 1"
        ).scalar_one()
    assert "image_url" in columns
    assert name == "Existing"
    legacy_engine.dispose()


def test_existing_users_get_a_username_from_their_email():
    legacy_engine = create_engine("sqlite://")
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(320) NOT NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO users (id, email) VALUES (1, 'old.user@example.com')"
        )

    upgrade_existing_usernames(legacy_engine)

    with legacy_engine.connect() as connection:
        username = connection.exec_driver_sql(
            "SELECT username FROM users WHERE id = 1"
        ).scalar_one()
    assert username == "old.user"
    legacy_engine.dispose()
