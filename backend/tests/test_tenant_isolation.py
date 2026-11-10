import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-stockflow-only")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db, upgrade_existing_usernames
from app.main import app
from app import models  # noqa: F401


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
    assert response.json()["user"]["username"] == email.partition("@")[0]
    return response.json()["access_token"]


def test_tenant_cannot_read_update_or_delete_another_organizations_product(
    client: TestClient,
):
    token_a = _signup(client, "user-a@example.com", "Organization A")
    token_b = _signup(client, "user-b@example.com", "Organization B")

    product_response = client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"name": "Private stock", "sku": "PRIVATE-1", "quantity_on_hand": 12},
    )
    assert product_response.status_code == 201
    product_id = product_response.json()["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    read_response = client.get(f"/api/products/{product_id}", headers=headers_a)
    assert read_response.status_code == 404

    update_response = client.put(
        f"/api/products/{product_id}",
        headers=headers_a,
        json={"name": "Compromised"},
    )
    assert update_response.status_code == 404

    delete_response = client.delete(f"/api/products/{product_id}", headers=headers_a)
    assert delete_response.status_code == 404

    owner_read = client.get(
        f"/api/products/{product_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert owner_read.status_code == 200
    assert owner_read.json()["name"] == "Private stock"


def test_inventory_dashboard_settings_and_stock_adjustment_flow(client: TestClient):
    token = _signup(client, "inventory@example.com", "Inventory Org")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api/products",
        headers=headers,
        json={"name": "Widget", "sku": "W-1", "quantity_on_hand": 3},
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    duplicate = client.post(
        "/api/products",
        headers=headers,
        json={"name": "Duplicate", "sku": "W-1"},
    )
    assert duplicate.status_code == 409

    dashboard = client.get("/api/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json() == {
        "total_products": 1,
        "total_quantity": 3,
        "low_stock_items": [
            {"name": "Widget", "sku": "W-1", "quantity_on_hand": 3, "threshold": 5}
        ],
    }

    settings = client.put(
        "/api/settings",
        headers=headers,
        json={"default_low_stock_threshold": 2},
    )
    assert settings.status_code == 200
    assert settings.json()["default_low_stock_threshold"] == 2
    dashboard = client.get("/api/dashboard", headers=headers)
    assert dashboard.json()["low_stock_items"] == []

    adjusted = client.post(
        f"/api/products/{product_id}/adjust",
        headers=headers,
        json={"delta": -1, "note": "One item sold"},
    )
    assert adjusted.status_code == 200
    assert adjusted.json()["quantity_on_hand"] == 2
    dashboard = client.get("/api/dashboard", headers=headers)
    assert dashboard.json()["low_stock_items"][0]["threshold"] == 2

    rejected_adjustment = client.post(
        f"/api/products/{product_id}/adjust",
        headers=headers,
        json={"delta": -3, "note": "Invalid negative inventory"},
    )
    assert rejected_adjustment.status_code == 422


def test_signup_rejects_blank_organization_name(client: TestClient):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "blank-org@example.com",
            "password": "secure-password-123",
            "organization_name": "   ",
        },
    )
    assert response.status_code == 422


def test_product_image_upload_is_persisted_and_tenant_scoped(client: TestClient):
    token_a = _signup(client, "image-a@example.com", "Image Org A")
    token_b = _signup(client, "image-b@example.com", "Image Org B")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    created = client.post(
        "/api/products",
        headers=headers_b,
        json={"name": "Photo item", "sku": "PHOTO-1"},
    )
    product_id = created.json()["id"]
    png_content = b"\x89PNG\r\n\x1a\n" + b"test-image-bytes"

    upload = client.put(
        f"/api/products/{product_id}/image",
        headers=headers_b,
        files={"image": ("photo.png", png_content, "image/png")},
    )
    assert upload.status_code == 200
    assert upload.json()["image_url"] == f"/products/{product_id}/image"

    product_list = client.get("/api/products", headers=headers_b)
    assert product_list.json()[0]["image_url"] == f"/products/{product_id}/image"

    image = client.get(f"/api/products/{product_id}/image", headers=headers_b)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content == png_content

    assert client.get(f"/api/products/{product_id}/image", headers=headers_a).status_code == 404
    assert client.put(
        f"/api/products/{product_id}/image",
        headers=headers_a,
        files={"image": ("photo.png", png_content, "image/png")},
    ).status_code == 404

    invalid_upload = client.put(
        f"/api/products/{product_id}/image",
        headers=headers_b,
        files={"image": ("not-image.png", b"not an image", "image/png")},
    )
    assert invalid_upload.status_code == 415

    assert client.delete(f"/api/products/{product_id}/image", headers=headers_b).status_code == 204
    assert client.get(f"/api/products/{product_id}/image", headers=headers_b).status_code == 404


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
