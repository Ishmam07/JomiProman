"""JomiProman API entry point."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import DEFAULT_ADMIN_KEY, DEFAULT_REGISTRAR_KEY, get_settings
from app.database import SessionLocal, init_db
from app.deps import get_ai, get_cache, get_signer
from app.errors import DomainError
from app.routers import admin, assistant, deeds, plots, system, verify
from app.seed import seed_demo

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("jomiproman")

FIELD_BN = {
    "mouza": "মৌজা",
    "dag": "দাগ নম্বর",
    "seller": "বিক্রেতা",
    "buyer": "ক্রেতা",
    "area": "জমির পরিমাণ",
    "deed_date": "তারিখ",
    "deed_no": "দলিল নম্বর",
    "question": "প্রশ্ন",
    "text": "লেখা",
    "hash": "হ্যাশ",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.is_production and settings.registrar_key == DEFAULT_REGISTRAR_KEY:
        raise RuntimeError("Set a strong REGISTRAR_KEY before running in production")
    if settings.is_production and settings.admin_key == DEFAULT_ADMIN_KEY:
        raise RuntimeError("Set a strong ADMIN_KEY before running in production")

    init_db()
    signer = get_signer()
    cache = get_cache()
    ai = get_ai()
    log.info(
        "Started v%s | env=%s | db=%s | cache=%s | ai=%s | signing key id=%s",
        __version__,
        settings.environment,
        "sqlite" if settings.is_sqlite else "mysql",
        cache.backend,
        "groq" if ai.enabled else "fallback",
        signer.key_id,
    )
    if settings.auto_seed:
        with SessionLocal() as db:
            seed_demo(db, signer)
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Tamper-evident land-deed ledger with automatic fraud checks, built for the "
        "LandTech Innovation Hackathon 2026. All data is dummy data."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Registrar-Key", "X-Admin-Key"],
)


@app.middleware("http")
async def access_log(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - started) * 1000
    if request.url.path != "/api/health":
        log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code, ms)
    return response


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, **({"data": exc.data} if exc.data else {})}},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    fields = []
    for err in exc.errors():
        name = str(err["loc"][-1]) if err.get("loc") else "?"
        fields.append(FIELD_BN.get(name, name))
    unique = list(dict.fromkeys(fields))
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "ইনপুট ঠিক নেই: " + "، ".join(unique), "fields": unique}},
    )


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception):
    log.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "server_error", "message": "সার্ভারে সমস্যা হয়েছে। একটু পরে আবার চেষ্টা করুন।"}},
    )


for router in (system.router, deeds.router, verify.router, plots.router, assistant.router, admin.router):
    app.include_router(router, prefix="/api")
