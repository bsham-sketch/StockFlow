import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./stockflow.db")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


DATABASE_URL = _database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def upgrade_existing_usernames(database_engine=engine) -> None:
    user_columns = {
        column["name"] for column in inspect(database_engine).get_columns("users")
    }
    if "username" not in user_columns:
        with database_engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(80)"))

    with database_engine.begin() as connection:
        existing_users = connection.execute(
            text("SELECT id, email FROM users WHERE username IS NULL OR trim(username) = ''")
        ).all()
        for user_id, email in existing_users:
            connection.execute(
                text("UPDATE users SET username = :username WHERE id = :user_id"),
                {"username": email.partition("@")[0], "user_id": user_id},
            )


def upgrade_product_image_url(database_engine=engine) -> None:
    product_columns = {
        column["name"] for column in inspect(database_engine).get_columns("products")
    }
    if "image_url" not in product_columns:
        with database_engine.begin() as connection:
            connection.execute(text("ALTER TABLE products ADD COLUMN image_url VARCHAR(2048)"))


def initialize_database() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    upgrade_existing_usernames()
    upgrade_product_image_url()
