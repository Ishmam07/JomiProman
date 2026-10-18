"""Read-only administrator console and privacy-conscious audit endpoints."""
import csv
from datetime import date, datetime, time
from io import StringIO
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import cast, func, or_, select, String
from sqlalchemy.orm import Session, selectinload

from app import __version__
from app.config import Settings, get_settings
from app.database import get_db
from app.deps import get_ai, get_cache, get_signer, require_admin
from app.models import AuditEvent, BLOCKED, REGISTERED, Deed, Plot
from app.security import Signer
from app.services.ai import AIService
from app.services.audit import record_event
from app.services.cache import Cache
from app.services.serializers import deed_to_dict

router = APIRouter(
    prefix="/admin",
    tags=["Admin console"],
    dependencies=[Depends(require_admin)],
)


def _event_dict(item: AuditEvent) -> dict[str, Any]:
    return {
        "id": item.id,
        "actor_type": item.actor_type,
        "action": item.action,
        "entity_type": item.entity_type,
        "entity_id": item.entity_id,
        "outcome": item.outcome,
        "summary": item.summary,
        "client_ip": item.client_ip,
        "details": item.details or {},
        "created_at": item.created_at.isoformat() + "Z" if item.created_at else None,
    }


def _plot_dict(plot: Plot) -> dict[str, Any]:
    return {
        "id": plot.id,
        "mouza": plot.mouza,
        "dag": plot.dag,
        "khatian_no": plot.khatian_no,
        "land_type": plot.land_type,
        "total_area": float(plot.total_area),
        "has_bank_lien": plot.has_bank_lien,
        "lien_bank": plot.lien_bank,
        "has_court_case": plot.has_court_case,
        "case_ref": plot.case_ref,
        "is_khas": plot.is_khas,
        "latitude": plot.latitude,
        "longitude": plot.longitude,
        "address": plot.address,
        "holder_count": len(plot.holdings),
        "deed_count": len(plot.deeds),
        "created_at": plot.created_at.isoformat() + "Z" if plot.created_at else None,
    }


def _matching_deeds(db: Session, q: str | None, status: str | None, risk: str | None, mutation: str | None):
    stmt = select(Deed).options(selectinload(Deed.plot)).order_by(Deed.id.desc())
    if status:
        stmt = stmt.where(Deed.status == status.upper())
    if risk:
        stmt = stmt.where(Deed.risk == risk.upper())
    if mutation:
        stmt = stmt.where(Deed.mutation_status == mutation.upper())
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.join(Deed.plot).where(or_(
            Deed.deed_no.ilike(needle), Deed.seller.ilike(needle), Deed.buyer.ilike(needle),
            Plot.mouza.ilike(needle), cast(Plot.dag, String).like(needle),
        ))
    return stmt


@router.get("/overview", summary="Administrative overview and system health")
def overview(
    request: Request,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    ai: AIService = Depends(get_ai),
    signer: Signer = Depends(get_signer),
    settings: Settings = Depends(get_settings),
):
    # Record successful admin overview access; never store the submitted admin key.
    record_event(db, request, action="admin.overview.view", actor_type="admin", entity_type="system",
                 outcome="ok", summary="Administrator overview opened.",
                 details={"environment": settings.environment})
    plots = int(db.scalar(select(func.count(Plot.id))) or 0)
    total_deeds = int(db.scalar(select(func.count(Deed.id))) or 0)
    registered = int(db.scalar(select(func.count(Deed.id)).where(Deed.status == REGISTERED)) or 0)
    blocked = int(db.scalar(select(func.count(Deed.id)).where(Deed.status == BLOCKED)) or 0)
    flagged = int(db.scalar(select(func.count(Deed.id)).where(or_(Deed.status == BLOCKED, Deed.risk == "AMBER"))) or 0)
    pending = int(db.scalar(select(func.count(Deed.id)).where(Deed.mutation_status == "PENDING", Deed.status == REGISTERED)) or 0)
    mutation_done = int(db.scalar(select(func.count(Deed.id)).where(Deed.mutation_status == "DONE")) or 0)
    risk_counts = {
        level: int(db.scalar(select(func.count(Deed.id)).where(Deed.risk == level)) or 0)
        for level in ("GREEN", "AMBER", "RED")
    }
    start_today = datetime.combine(date.today(), time.min)
    activity_today = int(db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.created_at >= start_today)) or 0)
    audits_total = int(db.scalar(select(func.count(AuditEvent.id))) or 0)
    recent_events = db.execute(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(12)).scalars().all()
    recent_deeds = db.execute(
        select(Deed).options(selectinload(Deed.plot)).order_by(Deed.id.desc()).limit(8)
    ).scalars().all()
    return {
        "version": __version__,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "metrics": {
            "plots": plots, "deeds_total": total_deeds, "deeds_registered": registered,
            "deeds_blocked": blocked, "deeds_flagged": flagged,
            "mutation_pending": pending, "mutation_done": mutation_done,
            "audit_events_total": audits_total, "activity_today": activity_today,
        },
        "risk_breakdown": risk_counts,
        "services": {
            "database": "up",
            "cache": cache.backend,
            "ai_enabled": ai.enabled,
            "ai_model": ai.model if ai.enabled else None,
            "signing_algorithm": "Ed25519",
            "signing_key_id": signer.key_id,
            "environment": settings.environment,
            "demo_data_enabled": settings.auto_seed,
        },
        "recent_events": [_event_dict(x) for x in recent_events],
        "recent_deeds": [deed_to_dict(x, settings) for x in recent_deeds],
    }


@router.get("/audit", summary="Search and page through the activity audit log")
def audit_log(
    q: str | None = Query(default=None, max_length=120),
    action: str | None = Query(default=None, max_length=80),
    outcome: str | None = Query(default=None, max_length=24),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if outcome:
        stmt = stmt.where(AuditEvent.outcome == outcome.lower())
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            AuditEvent.summary.ilike(needle), AuditEvent.entity_id.ilike(needle),
            AuditEvent.action.ilike(needle), AuditEvent.client_ip.ilike(needle),
        ))
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.execute(stmt.order_by(AuditEvent.id.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [_event_dict(x) for x in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/deeds", summary="Search deed ledger for administrative review")
def deeds(
    q: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None, pattern="^(REGISTERED|BLOCKED)$"),
    risk: str | None = Query(default=None, pattern="^(GREEN|AMBER|RED)$"),
    mutation: str | None = Query(default=None, pattern="^(NA|PENDING|DONE)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    stmt = _matching_deeds(db, q, status, risk, mutation)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [deed_to_dict(x, settings) for x in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/plots", summary="Search land plots and current record flags")
def plots(
    q: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(Plot).options(selectinload(Plot.holdings), selectinload(Plot.deeds)).order_by(Plot.id.desc())
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(Plot.mouza.ilike(needle), Plot.khatian_no.ilike(needle), cast(Plot.dag, String).like(needle)))
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [_plot_dict(x) for x in rows], "total": total, "page": page, "page_size": page_size}


def _csv_cell(value: Any) -> Any:
    """Prevent spreadsheet formula execution for untrusted text fields in exports."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


@router.get("/audit.csv", summary="Export the activity audit log as CSV")
def export_audit_csv(request: Request, db: Session = Depends(get_db)):
    rows = db.execute(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(10000)).scalars().all()
    record_event(db, request, action="admin.audit.export", actor_type="admin", entity_type="audit_log",
                 outcome="ok", summary="Administrator exported the audit log.", details={"row_count": len(rows)})
    # Include the export event itself where possible.
    rows = db.execute(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(10000)).scalars().all()
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(["id", "created_at_utc", "actor_type", "action", "entity_type", "entity_id", "outcome", "summary", "client_ip", "details_json"])
    for item in rows:
        writer.writerow([
            item.id, _csv_cell(item.created_at.isoformat() + "Z" if item.created_at else ""),
            _csv_cell(item.actor_type), _csv_cell(item.action), _csv_cell(item.entity_type),
            _csv_cell(item.entity_id or ""), _csv_cell(item.outcome), _csv_cell(item.summary),
            _csv_cell(item.client_ip or ""), _csv_cell(__import__("json").dumps(item.details or {}, ensure_ascii=False)),
        ])
    from fastapi.responses import Response
    return Response(
        content="\ufeff" + stream.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=jomiproman-audit.csv"},
    )
