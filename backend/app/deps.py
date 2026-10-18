"""FastAPI dependencies and process-wide singletons."""

import secrets
from collections.abc import Callable
from functools import lru_cache

from fastapi import Depends, Header, Request

from app.config import Settings, get_settings
from app.errors import RateLimited, Unauthorized
from app.security import Signer, load_signer
from app.database import get_db
from app.models import AuditEvent
from app.services.audit import record_event
from sqlalchemy.orm import Session
from app.services.ai import AIService
from app.services.cache import Cache


@lru_cache
def get_cache() -> Cache:
    return Cache(get_settings().redis_url)


@lru_cache
def get_signer() -> Signer:
    return load_signer(get_settings())


@lru_cache
def get_ai() -> AIService:
    return AIService(get_settings(), get_cache())


def settings_dep() -> Settings:
    return get_settings()


def require_registrar(
    request: Request,
    x_registrar_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    """Only the (simulated) sub-registrar / land office may write to the ledger."""
    expected = get_settings().registrar_key
    if not x_registrar_key or not secrets.compare_digest(x_registrar_key, expected):
        # Log an unauthorized attempt without ever recording the supplied key.
        record_event(
            db, request, action="registrar.access.denied", actor_type="anonymous",
            entity_type="registrar", outcome="denied",
            summary="Rejected an invalid registrar access attempt.", details={},
        )
        raise Unauthorized(
            "রেজিস্ট্রার কী সঠিক নয়। শুধু অনুমোদিত কর্মকর্তা দলিল নিবন্ধন করতে পারেন।",
            code="invalid_registrar_key",
        )


def require_admin(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    db: Session = Depends(get_db),
) -> None:
    """Protect admin APIs with a separate key; failed access attempts are logged."""
    expected = get_settings().admin_key
    if not expected or not x_admin_key or not secrets.compare_digest(x_admin_key, expected):
        # Keep the audit trail useful without storing the supplied key.
        try:
            db.add(AuditEvent(
                actor_type="anonymous", action="admin.access.denied", entity_type="admin",
                outcome="denied", summary="Rejected an invalid admin access attempt.",
                client_ip=request.client.host if request.client else None, details={},
            ))
            db.commit()
        except Exception:  # noqa: BLE001 - an audit failure must not leak an exception here
            db.rollback()
        raise Unauthorized("অ্যাডমিন কী সঠিক নয়। .env ফাইলে ADMIN_KEY দেখুন।", code="invalid_admin_key")


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        settings = get_settings()
        key = f"rl:{scope}:{client_ip(request)}"
        if get_cache().hit(key, 60) > settings.rate_limit_per_minute:
            raise RateLimited(
                "অনেক বেশি অনুরোধ পাঠানো হয়েছে। এক মিনিট পরে আবার চেষ্টা করুন।",
                code="rate_limited",
            )

    return dependency
