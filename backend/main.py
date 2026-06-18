import os
import time
import uuid
import uvicorn
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from database import engine, Base
from routers import auth, bills, categories, fitness, stats, settings, data

load_dotenv()

START_TIME = time.time()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="抱布记 API", version="1.0.0")


def check_db() -> str:
    """Return 'ok' if the database is reachable, otherwise 'error'."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


# ---------------------------------------------------------------------------
# Middleware: X-Request-ID
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handlers — uniform JSON error responses
# ---------------------------------------------------------------------------
async def _error_response(status_code: int, detail: str, request_id: str | None = None) -> JSONResponse:
    body = {"error": True, "detail": detail, "code": status_code}
    if request_id:
        body["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return await _error_response(
        status_code=exc.status_code,
        detail=exc.detail,
        request_id=request.headers.get("X-Request-ID"),
    )


# Override FastAPI's built-in 404/405 handlers for unmatched routes
@app.exception_handler(404)
async def not_found_404(request: Request, exc):
    return await _error_response(status_code=404, detail="Not Found",
                                 request_id=request.headers.get("X-Request-ID"))


@app.exception_handler(405)
async def not_found_405(request: Request, exc):
    return await _error_response(status_code=405, detail="Method Not Allowed",
                                 request_id=request.headers.get("X-Request-ID"))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    detail = str(exc)
    if not app.debug:
        detail = "Request validation failed"
    return await _error_response(
        status_code=422,
        detail=detail,
        request_id=request.headers.get("X-Request-ID"),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    detail = str(exc)
    if not app.debug:
        detail = "Internal server error"
    return await _error_response(
        status_code=500,
        detail=detail,
        request_id=request.headers.get("X-Request-ID"),
    )


app.include_router(auth.router)
app.include_router(bills.router)
app.include_router(categories.router)
app.include_router(fitness.router)
app.include_router(stats.router)
app.include_router(settings.router)
app.include_router(data.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "抱布记",
        "version": "1.0.0",
        "uptime": round(time.time() - START_TIME, 2),
        "database": check_db(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8089"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
