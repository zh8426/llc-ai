import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.datasheets import router as datasheets_router
from app.api.diagnosis import router as diagnosis_router
from app.api.errors import APIError, api_error_response
from app.api.fault_cases import router as fault_cases_router
from app.api.health import router as health_router
from app.api.llm import router as llm_router
from app.api.projects import router as projects_router
from app.api.reports import history_router as historical_reports_router
from app.api.reports import router as reports_router
from app.api.reviews import history_router as review_history_router
from app.api.reviews import router as reviews_router
from app.api.waveforms import router as waveforms_router
from app.schemas.errors import ErrorCode

app = FastAPI(
    title="LLC Engineering Assistant API",
    description=(
        "Project persistence, deterministic LLC calculations, design review, and waveform APIs."
    ),
    version="0.1.0",
)


@app.exception_handler(APIError)
async def handle_api_error(_request: Request, error: APIError) -> JSONResponse:
    return api_error_response(error)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    details = {
        "errors": [
            {
                "location": list(item.get("loc", ())),
                "message": item.get("msg", "Invalid request value."),
                "type": item.get("type", "request_error"),
            }
            for item in error.errors()
        ]
    }
    return api_error_response(
        APIError(
            422,
            "INVALID_REQUEST",
            "请求参数无效。",
            details=details,
        )
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(
    _request: Request, error: StarletteHTTPException
) -> JSONResponse:
    code: ErrorCode
    if error.status_code == 404:
        code = "RESOURCE_NOT_FOUND"
        message = "请求的资源不存在。"
    elif error.status_code == 405:
        code = "METHOD_NOT_ALLOWED"
        message = "请求方法不被允许。"
    else:
        code = "INVALID_REQUEST"
        message = "请求无效。"
    return api_error_response(
        APIError(error.status_code, code, message, details=None)
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
    return api_error_response(
        APIError(500, "INTERNAL_ERROR", "服务器内部错误，请稍后重试。")
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
app.include_router(datasheets_router)
app.include_router(fault_cases_router)
app.include_router(diagnosis_router)
app.include_router(llm_router)
