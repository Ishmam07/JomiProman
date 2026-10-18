from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.deps import get_cache, get_signer, require_registrar
from app.errors import NotFound
from app.models import BLOCKED, REGISTERED, Deed
from app.schemas import DeedCreate, DeedOut
from app.security import Signer
from app.services.cache import Cache
from app.services.audit import record_event
from app.services.ledger import complete_mutation, register_deed
from app.services.plot_view import invalidate_plot
from app.services.qr import make_qr_png
from app.services.serializers import deed_to_dict, verify_url

router = APIRouter(prefix="/deeds", tags=["Deeds"])


def _load(db: Session, deed_no: str) -> Deed:
    deed = db.execute(select(Deed).where(Deed.deed_no == deed_no.strip().upper())).scalar_one_or_none()
    if deed is None:
        raise NotFound("দলিল পাওয়া যায়নি।", code="deed_not_found")
    return deed


@router.post(
    "",
    response_model=DeedOut,
    status_code=201,
    dependencies=[Depends(require_registrar)],
    summary="Register a deed (runs the fraud rules first)",
)
def create_deed(
    payload: DeedCreate,
    request: Request,
    db: Session = Depends(get_db),
    signer: Signer = Depends(get_signer),
    cache: Cache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
):
    """Accepted deeds are hash-chained, signed and get a QR code.
    Deeds that trip a RED rule are stored as BLOCKED for audit and never move land."""
    deed = register_deed(db, payload, signer)
    invalidate_plot(cache, deed.plot.mouza, deed.plot.dag)
    record_event(
        db, request, action="deed.register", actor_type="registrar", entity_type="deed",
        entity_id=deed.deed_no, outcome=deed.status.lower(),
        summary=f"Deed {deed.deed_no} evaluated: {deed.status} ({deed.risk}).",
        details={"status": deed.status, "risk": deed.risk, "rule_codes": [x.get("code") for x in (deed.findings or [])]},
    )
    return deed_to_dict(deed, settings)


@router.get("/flagged", response_model=list[DeedOut], summary="Blocked and suspicious deeds")
def flagged(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    stmt = (
        select(Deed)
        .where(or_(Deed.status == BLOCKED, Deed.risk == "AMBER"))
        .order_by(Deed.id.desc())
        .limit(100)
    )
    rows = db.execute(stmt).scalars().all()
    record_event(db, request, action="deed.flagged_list.view", actor_type="public", entity_type="deed_list",
                 outcome="ok", summary="Flagged-deed list viewed.", details={"result_count": len(rows)})
    return [deed_to_dict(d, settings) for d in rows]


@router.get("", response_model=list[DeedOut], summary="Most recent deeds")
def recent(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    stmt = select(Deed).order_by(Deed.id.desc()).limit(50)
    rows = db.execute(stmt).scalars().all()
    record_event(db, request, action="deed.recent_list.view", actor_type="public", entity_type="deed_list",
                 outcome="ok", summary="Recent-deed list viewed.", details={"result_count": len(rows)})
    return [deed_to_dict(d, settings) for d in rows]


@router.get("/{deed_no}", response_model=DeedOut)
def get_deed(
    deed_no: str, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    deed = _load(db, deed_no)
    record_event(db, request, action="deed.record.view", actor_type="public", entity_type="deed",
                 entity_id=deed.deed_no, outcome="ok", summary=f"Deed {deed.deed_no} record viewed.",
                 details={"status": deed.status, "risk": deed.risk})
    return deed_to_dict(deed, settings)


@router.get(
    "/{deed_no}/qr",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
    summary="QR code (PNG) that links to the verification page",
)
def deed_qr(
    deed_no: str, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    deed = _load(db, deed_no)
    if deed.status != REGISTERED:
        raise NotFound("আটকানো দলিলের জন্য QR কোড নেই।", code="no_qr_for_blocked")
    record_event(db, request, action="deed.qr_generated", actor_type="public", entity_type="deed",
                 entity_id=deed.deed_no, outcome="ok", summary=f"Verification QR generated for deed {deed.deed_no}.")
    return Response(
        content=make_qr_png(verify_url(settings, deed)),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.post(
    "/{deed_no}/mutation",
    response_model=DeedOut,
    dependencies=[Depends(require_registrar)],
    summary="Complete e-Mutation for a registered deed",
)
def mutate(
    deed_no: str,
    request: Request,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
):
    deed = complete_mutation(db, deed_no.strip().upper())
    invalidate_plot(cache, deed.plot.mouza, deed.plot.dag)
    record_event(
        db, request, action="deed.mutation.completed", actor_type="registrar", entity_type="deed",
        entity_id=deed.deed_no, outcome="ok", summary=f"Mutation completed for deed {deed.deed_no}.",
        details={"mutation_status": deed.mutation_status},
    )
    return deed_to_dict(deed, settings)
