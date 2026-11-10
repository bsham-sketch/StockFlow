from contextlib import asynccontextmanager
import os
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import initialize_database
from app.routers import auth, dashboard, products, settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be configured in the environment.")
    initialize_database()
    yield


app = FastAPI(title="StockFlow API", version="1.0.0", lifespan=lifespan)

origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(dashboard.router)
app.include_router(settings.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
