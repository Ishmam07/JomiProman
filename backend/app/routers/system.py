from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app import __version__
from app.config import Settings, get_settings
from app.database import get_db
from app.deps import get_ai, get_cache, get_signer, require_registrar
from app.errors import DomainError
from app.models import BLOCKED, REGISTERED, Deed, Plot
from app.schemas import Stats
from app.security import Signer
from app.seed import reset_data, seed_demo
from app.services.ai import AIService
from app.services.audit import record_event
from app.services.cache import Cache

router = APIRouter(tags=["System"])


@router.get("/health", summary="Liveness / readiness probe")
def health(
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    ai: AIService = Depends(get_ai),
):
    try:
        db.execute(text("SELECT 1"))
        database = "up"
    except Exception:  # noqa: BLE001
        database = "down"
    body = {
        "status": "ok" if database == "up" else "degraded",
        "version": __version__,
        "database": database,
        "cache": cache.backend,
        "ai": "configured" if ai.enabled else "fallback-mode",
    }
    return JSONResponse(body, status_code=200 if database == "up" else 503)


@router.get("/stats", response_model=Stats, summary="Numbers for the home page")
def stats(
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    ai: AIService = Depends(get_ai),
):
    plots = db.scalar(select(func.count(Plot.id))) or 0
    registered = db.scalar(select(func.count(Deed.id)).where(Deed.status == REGISTERED)) or 0
    blocked = db.scalar(select(func.count(Deed.id)).where(Deed.status == BLOCKED)) or 0
    attention = (
        db.scalar(select(func.count(Deed.id)).where(or_(Deed.status == BLOCKED, Deed.risk == "AMBER")))
        or 0
    )
    return {
        "plots": plots,
        "deeds_registered": registered,
        "deeds_blocked": blocked,
        "deeds_need_attention": attention,
        "cache_backend": cache.backend,
        "ai_enabled": ai.enabled,
    }


@router.get("/public-key", summary="Sub-registrar public key (to verify signatures independently)")
def public_key(signer: Signer = Depends(get_signer)):
    return {"algorithm": "Ed25519", "key_id": signer.key_id, "public_key_hex": signer.public_key_hex}


@router.post(
    "/seed",
    dependencies=[Depends(require_registrar)],
    summary="Load (or reset to) the dummy demo dataset",
)
def seed(
    request: Request,
    reset: bool = False,
    db: Session = Depends(get_db),
    signer: Signer = Depends(get_signer),
    cache: Cache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
):
    if settings.is_production:
        raise DomainError("প্রোডাকশনে ডেমো ডেটা লোড করা যায় না।", code="seed_disabled", status_code=403)
    if reset:
        reset_data(db)
    created = seed_demo(db, signer)
    cache.clear_memory()
    record_event(db, request, action="system.demo_seed", actor_type="registrar", entity_type="dataset",
                 outcome="ok", summary=f"Demo dataset operation completed (seeded={created}, reset={reset}).",
                 details={"seeded": created, "reset": reset})
    return {"seeded": created, "reset": reset}
