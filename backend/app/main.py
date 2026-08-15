import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.reports import history_router as historical_reports_router
from app.api.reports import router as reports_router
from app.api.reviews import history_router as review_history_router
from app.api.reviews import router as reviews_router
from app.api.waveforms import router as waveforms_router

app = FastAPI(
    title="LLC Engineering Assistant API",
    description=(
        "Project persistence, deterministic LLC calculations, design review, and waveform APIs."
    ),
    version="0.1.0",
)
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(health_router)
app.include_router(projects_router)
app.include_router(reviews_router)
app.include_router(review_history_router)
app.include_router(reports_router)
app.include_router(historical_reports_router)
app.include_router(waveforms_router)
