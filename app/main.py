from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import health, logs, processing
from .utils.file_ops import cleanup_storage


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover - startup side effects
    init_db()
    cleanup_storage(
        directories=[
            settings.storage_root / "uploads",
            settings.storage_root / "processed",
        ],
        retention_hours=settings.temp_retention_hours,
    )
    yield


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="API for detecting and masking QR codes in uploaded images.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(processing.router)
app.include_router(logs.router)
