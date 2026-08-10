from fastapi import FastAPI

from app.api.health import router as health_router


app = FastAPI(
    title="LLC Engineering Assistant API",
    description=(
        "Backend with deterministic LLC core calculations and design review rules. "
        "Project and review REST APIs are not implemented yet."
    ),
    version="0.1.0",
)
app.include_router(health_router)
