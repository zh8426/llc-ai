from fastapi import FastAPI

from app.api.health import router as health_router


app = FastAPI(
    title="LLC Engineering Assistant API",
    description="Phase 0 application skeleton. No LLC engineering logic is implemented.",
    version="0.1.0",
)
app.include_router(health_router)

