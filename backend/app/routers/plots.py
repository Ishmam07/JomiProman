from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.deps import get_cache, get_signer, require_registrar
from app.models import Plot
from app.schemas import ChainOut, LocationIn, PlotListItem, PlotView
from app.security import Signer
from app.services.cache import Cache
from app.services.audit import record_event
from app.services.ledger import get_plot, verify_chain
from app.services.plot_view import get_plot_view, invalidate_plot

router = APIRouter(prefix="/plots", tags=["Plots (Check before you buy)"])


@router.get("", response_model=list[PlotListItem], summary="Known plots (for search suggestions)")
def list_plots(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Plot.mouza, Plot.dag, Plot.latitude, Plot.longitude).order_by(Plot.mouza, Plot.dag)
    ).all()
    return [{"mouza": m, "dag": d, "latitude": la, "longitude": lo} for m, d, la, lo in rows]


@router.get("/{mouza}/{dag}", response_model=PlotView, summary="Everything a buyer should know about a plot")
def plot_check(
    mouza: str,
    dag: int,
    request: Request,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    signer: Signer = Depends(get_signer),
    settings: Settings = Depends(get_settings),
):
    result = get_plot_view(db, cache, settings, signer, mouza, dag)
    record_event(
        db, request, action="land.plot_check", actor_type="public", entity_type="plot",
        entity_id=f"{mouza}/{dag}", outcome=result["status"].lower(),
        summary=f"Plot check returned {result['status']} for {mouza}/{dag}.",
        details={"status": result["status"], "finding_count": len(result["findings"]), "chain_valid": result["chain"]["valid"]},
    )
    return result


@router.get("/{mouza}/{dag}/chain", response_model=ChainOut, summary="Re-verify the whole ledger chain now")
def plot_chain(
    mouza: str,
    dag: int,
    request: Request,
    db: Session = Depends(get_db),
    signer: Signer = Depends(get_signer),
):
    result = verify_chain(get_plot(db, mouza, dag), signer)
    payload = result.to_dict()
    record_event(
        db, request, action="land.chain.verify", actor_type="public", entity_type="plot",
        entity_id=f"{mouza}/{dag}", outcome="ok" if payload["valid"] else "red",
        summary=f"Ledger chain check {'passed' if payload['valid'] else 'failed'} for {mouza}/{dag}.",
        details={"valid": payload["valid"], "length": payload["length"], "reason": payload["reason"]},
    )
    return payload


@router.put(
    "/{mouza}/{dag}/location",
    response_model=PlotView,
    dependencies=[Depends(require_registrar)],
    summary="Set the map location of a plot (registrar only)",
)
def set_location(
    mouza: str,
    dag: int,
    request: Request,
    payload: LocationIn,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    signer: Signer = Depends(get_signer),
    settings: Settings = Depends(get_settings),
):
    plot = get_plot(db, mouza, dag)
    plot.latitude = payload.latitude
    plot.longitude = payload.longitude
    plot.address = payload.address
    db.commit()
    invalidate_plot(cache, plot.mouza, plot.dag)
    record_event(
        db, request, action="land.plot_location_updated", actor_type="registrar", entity_type="plot",
        entity_id=f"{plot.mouza}/{plot.dag}", outcome="ok",
        summary=f"Map location updated for {plot.mouza}/{plot.dag}.",
        details={"coordinates_present": True, "address_present": bool(payload.address)},
    )
    return get_plot_view(db, cache, settings, signer, plot.mouza, plot.dag)
