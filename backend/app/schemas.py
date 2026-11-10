from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


NonEmptyName = Annotated[str, Field(min_length=1, max_length=160)]
NonEmptySku = Annotated[str, Field(min_length=1, max_length=80)]
NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativePrice = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


def _validate_bcrypt_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be no more than 72 bytes.")
    return password


class SignupRequest(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=80)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    organization_name: NonEmptyName

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Username cannot be blank.")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("organization_name")
    @classmethod
    def normalize_organization_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Organization name cannot be blank.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        return _validate_bcrypt_password(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        return _validate_bcrypt_password(value)


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    organization_id: int
    organization_name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ProductBase(BaseModel):
    name: NonEmptyName
    sku: NonEmptySku
    description: Annotated[str | None, Field(max_length=2000)] = None
    quantity_on_hand: NonNegativeInt = 0
    cost_price: NonNegativePrice | None = None
    selling_price: NonNegativePrice | None = None
    low_stock_threshold: NonNegativeInt | None = None

    @field_validator("name", "sku")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field cannot be blank.")
        return normalized


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: NonEmptyName | None = None
    sku: NonEmptySku | None = None
    description: Annotated[str | None, Field(max_length=2000)] = None
    quantity_on_hand: NonNegativeInt | None = None
    cost_price: NonNegativePrice | None = None
    selling_price: NonNegativePrice | None = None
    low_stock_threshold: NonNegativeInt | None = None

    @field_validator("name", "sku")
    @classmethod
    def validate_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("This field cannot be null.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field cannot be blank.")
        return normalized


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime
    last_updated_by: int
    image_url: str | None = None


class StockAdjustment(BaseModel):
    delta: int
    note: Annotated[str, Field(min_length=1, max_length=500)]

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Note cannot be blank.")
        return normalized


class LowStockItem(BaseModel):
    name: str
    sku: str
    quantity_on_hand: int
    threshold: int


class DashboardResponse(BaseModel):
    total_products: int
    total_quantity: int
    low_stock_items: list[LowStockItem]


class SettingsResponse(BaseModel):
    default_low_stock_threshold: NonNegativeInt


class SettingsUpdate(BaseModel):
    default_low_stock_threshold: NonNegativeInt
