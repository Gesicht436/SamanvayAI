"""FastAPI application entry point for Samanvay."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.logging_setup import configure_logging, logger
from api.routers import audit_router, auth_router, health_router, ingest_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle handler."""
    settings = get_settings()
    configure_logging()
    logger.info("samanvay_api_startup", clock_mode=settings.clock_mode, demo_mode=settings.demo_mode)
    yield
    logger.info("samanvay_api_shutdown")


app = FastAPI(
    title="Samanvay Material Master Harmonization Platform",
    description="Unified Material Master platform for CPSEs (SIH26099).",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(ingest_router)

