"""Registration, mutation and chain verification for the per-plot ledger."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import Conflict, NotFound
from app.models import BLOCKED, REGISTERED, Deed, Holding, Plot
from app.schemas import DeedCreate
from app.security import Signer, fingerprint, genesis_hash, link_hash
from app.services import names
from app.services.rules import RED, evaluate_sale, find_holding


def deed_fingerprint(deed: Deed, plot: Plot) -> str:
    return fingerprint(
        deed_no=deed.deed_no or "",
        mouza=plot.mouza,
        dag=plot.dag,
        seller=deed.seller,
        buyer=deed.buyer,
        area=deed.area,
        deed_date=deed.deed_date,
    )


def get_plot(db: Session, mouza: str, dag: int, *, lock: bool = False) -> Plot:
    stmt = select(Plot).where(Plot.mouza == mouza, Plot.dag == dag)
    if lock:
        stmt = stmt.with_for_update()  # serialises concurrent sales of the same plot (MySQL)
    plot = db.execute(stmt).scalar_one_or_none()
    if plot is None:
        raise NotFound(f"মৌজা '{mouza}', দাগ {dag} সিস্টেমে পাওয়া যায়নি।", code="plot_not_found")
    return plot


def register_deed(db: Session, payload: DeedCreate, signer: Signer) -> Deed:
    """Run the fraud rules, then store the deed.

    RED   -> stored as BLOCKED (kept for audit, not chained, no land moves)
    other -> stored as REGISTERED, hash-chained, signed, holdings updated
    """
    plot = get_plot(db, payload.mouza, payload.dag, lock=True)
    holdings = list(plot.holdings)
    evaluation = evaluate_sale(plot, holdings, payload.seller, payload.buyer, payload.area)
    blocked = evaluation.risk == RED

    deed = Deed(
        plot_id=plot.id,
        seller=payload.seller,
        buyer=payload.buyer,
        area=payload.area,
        deed_date=payload.deed_date or date.today(),
        status=BLOCKED if blocked else REGISTERED,
        risk=evaluation.risk,
        findings=[f.to_dict() for f in evaluation.findings],
        mutation_status="NA" if blocked else "PENDING",
        created_at=datetime.utcnow(),
    )
    db.add(deed)
    db.flush()  # assigns deed.id
    deed.deed_no = f"D-{deed.id:04d}"
    deed.fingerprint = deed_fingerprint(deed, plot)

    if not blocked:
        last = db.execute(
            select(Deed)
            .where(Deed.plot_id == plot.id, Deed.status == REGISTERED, Deed.id != deed.id)
            .order_by(Deed.chain_index.desc())
            .limit(1)
        ).scalar_one_or_none()
        prev = last.record_hash if last else genesis_hash(plot.mouza, plot.dag)
        deed.prev_hash = prev
        deed.chain_index = (last.chain_index + 1) if last else 1
        deed.record_hash = link_hash(prev, deed.fingerprint)
        deed.signature = signer.sign(deed.record_hash)
        _move_land(plot, holdings, evaluation.seller_holding, deed)

    db.commit()
    db.refresh(deed)
    return deed


def _move_land(plot: Plot, holdings: list[Holding], seller: Holding | None, deed: Deed) -> None:
    assert seller is not None
    seller.area = Decimal(seller.area) - Decimal(deed.area)

    norm = names.normalize_name(deed.buyer) or deed.buyer.strip().lower()
    target, label = find_holding(holdings, deed.buyer)
    if target is None or label != names.SAME:
        target = Holding(
            plot_id=plot.id,
            holder_name=deed.buyer,
            holder_norm=norm,
            area=Decimal("0"),
            khatian_name=None,
        )
        plot.holdings.append(target)
    target.area = Decimal(target.area) + Decimal(deed.area)


def complete_mutation(db: Session, deed_no: str) -> Deed:
    """e-Mutation: the land office records the buyer's name in the khatian."""
    deed = db.execute(select(Deed).where(Deed.deed_no == deed_no)).scalar_one_or_none()
    if deed is None:
        raise NotFound("দলিল পাওয়া যায়নি।", code="deed_not_found")
    if deed.status != REGISTERED:
        raise Conflict("আটকানো দলিলের নামজারি করা যায় না।", code="deed_blocked")
    if deed.mutation_status == "DONE":
        raise Conflict("এই দলিলের নামজারি আগেই সম্পন্ন হয়েছে।", code="already_mutated")

    plot = deed.plot
    holding, _ = find_holding(list(plot.holdings), deed.buyer)
    if holding is not None:
        holding.khatian_name = holding.holder_name
    deed.mutation_status = "DONE"
    db.commit()
    db.refresh(deed)
    return deed


# ---------------------------------------------------------------------------
# Chain verification
# ---------------------------------------------------------------------------
@dataclass
class ChainStatus:
    valid: bool
    length: int
    broken_deed_no: str | None = None
    broken_index: int | None = None
    reason: str | None = None  # RECORD_TAMPERED | CHAIN_BROKEN | SIGNATURE_INVALID

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "length": self.length,
            "broken_deed_no": self.broken_deed_no,
            "reason": self.reason,
        }


def verify_chain(plot: Plot, signer: Signer) -> ChainStatus:
    """Recompute every fingerprint, link and signature of a plot's chain."""
    deeds = sorted(
        (d for d in plot.deeds if d.status == REGISTERED), key=lambda d: d.chain_index or 0
    )
    prev = genesis_hash(plot.mouza, plot.dag)
    for position, d in enumerate(deeds, start=1):
        if deed_fingerprint(d, plot) != d.fingerprint:
            return ChainStatus(False, len(deeds), d.deed_no, position, "RECORD_TAMPERED")
        if d.chain_index != position or d.prev_hash != prev:
            return ChainStatus(False, len(deeds), d.deed_no, position, "CHAIN_BROKEN")
        if link_hash(prev, d.fingerprint) != d.record_hash:
            return ChainStatus(False, len(deeds), d.deed_no, position, "CHAIN_BROKEN")
        if not signer.verify(d.record_hash or "", d.signature):
            return ChainStatus(False, len(deeds), d.deed_no, position, "SIGNATURE_INVALID")
        prev = d.record_hash or ""
    return ChainStatus(True, len(deeds))
