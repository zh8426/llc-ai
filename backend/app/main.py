from fastapi import FastAPI

from app.api.health import router as health_router


app = FastAPI(
    title="LLC Engineering Assistant API",
    description=(
        "Phase 1 backend with deterministic LLC core calculations. "
        "Calculation APIs and design review rules are not implemented yet."
    ),
    version="0.1.0",
)
app.include_router(health_router)
