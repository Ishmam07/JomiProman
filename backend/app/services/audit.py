"""Small helper for recording meaningful, privacy-conscious application events."""
import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditEvent

log = logging.getLogger(__name__)


def record_event(
    db: Session,
    request: Request | None,
    *,
    action: str,
    actor_type: str = "public",
    entity_type: str = "system",
    entity_id: str | int | None = None,
    outcome: str = "ok",
    summary: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Store an event. Never pass secrets, full prompts, or raw document text here.

    Audit persistence is best-effort after the business transaction has committed so a
    logging failure never makes a successful deed operation look failed to the caller.
    """
    try:
        db.add(AuditEvent(
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            outcome=outcome,
            summary=summary[:255],
            client_ip=request.client.host if request and request.client else None,
            details=details or {},
        ))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("Could not persist activity event %s", action)
