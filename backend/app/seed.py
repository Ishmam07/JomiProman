"""Dummy demo data. Every name, plot and case below is fictional."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.models import Deed, Holding, Plot
from app.schemas import DeedCreate
from app.security import Signer
from app.services import names
from app.services.ledger import complete_mutation, register_deed

log = logging.getLogger(__name__)

# (mouza, dag, total_area, khatian_no, owner, khatian_name, flags)
PLOTS = [
    # Main demo plot: sell 6 then try to sell 7 -> double-sale caught
    ("রহিমপুর", 412, "10", "১২৪", "করিম", "করিম", {}),
    # Land already mortgaged to a bank
    ("রহিমপুর", 413, "15", "১২৪", "সুলতানা বেগম", "সুলতানা বেগম",
     {"has_bank_lien": True, "lien_bank": "জনতা ব্যাংক, রহিমপুর শাখা"}),
    # Clean plot that already has one completed, mutated transfer
    ("রহিমপুর", 414, "12", "১২৫", "আনোয়ার হোসেন", "আনোয়ার হোসেন", {}),
    # Land under a court case
    ("চন্দনপুর", 101, "8", "৩১০", "জামাল উদ্দিন", "জামাল উদ্দিন",
     {"has_court_case": True, "case_ref": "দেওয়ানি মামলা নং ১২৩/২০২৪"}),
    # Khatian spells the owner differently -> amber (name variant)
    ("চন্দনপুর", 102, "12", "৩১০", "আব্দুল হক", "আব্দুল হাক", {}),
    # Government khas land
    ("শ্যামপুর", 55, "30", "৯০১", "বাংলাদেশ সরকার", "বাংলাদেশ সরকার",
     {"is_khas": True, "land_type": "খাস"}),
    # Clean plot, one transfer whose mutation is still pending -> amber
    ("শ্যামপুর", 56, "20", "৯০২", "নাসরিন আক্তার", "নাসরিন আক্তার", {}),
]


# Approximate fictional-ish coordinates (central Bangladesh) so the map has something to show.
COORDS = {
    ("রহিমপুর", 412): (23.8103, 90.4125), ("রহিমপুর", 413): (23.8110, 90.4135),
    ("রহিমপুর", 414): (23.8095, 90.4142), ("চন্দনপুর", 101): (24.0020, 90.4200),
    ("চন্দনপুর", 102): (24.0030, 90.4212), ("শ্যামপুর", 55): (23.7200, 90.3900),
    ("শ্যামপুর", 56): (23.7210, 90.3910),
}


def reset_data(db: Session) -> None:
    """Wipe demo data. Signed deeds are protected by DB triggers, so lift them for the reset."""
    from app.database import engine
    from app.db_guards import drop_guards, install_guards

    db.rollback()  # make sure this session holds no locks while we change triggers
    drop_guards(engine)
    try:
        db.execute(delete(Deed))
        db.execute(delete(Holding))
        db.execute(delete(Plot))
        db.commit()
        if engine.dialect.name != "sqlite":  # MySQL keeps counting after DELETE; restart so deed numbers begin at D-0001
            for table in ("deeds", "holdings", "plots"):
                db.execute(text(f"ALTER TABLE {table} AUTO_INCREMENT = 1"))
            db.commit()
    finally:
        install_guards(engine)


def seed_demo(db: Session, signer: Signer) -> bool:
    """Idempotent: does nothing if any plot already exists. Returns True if data was created."""
    if (db.scalar(select(func.count(Plot.id))) or 0) > 0:
        return False

    for mouza, dag, area, khatian_no, owner, khatian_name, flags in PLOTS:
        plot = Plot(
            mouza=mouza,
            dag=dag,
            total_area=Decimal(area),
            khatian_no=khatian_no,
            land_type=flags.get("land_type", "কৃষি"),
            has_bank_lien=flags.get("has_bank_lien", False),
            lien_bank=flags.get("lien_bank"),
            has_court_case=flags.get("has_court_case", False),
            case_ref=flags.get("case_ref"),
            is_khas=flags.get("is_khas", False),
            latitude=COORDS.get((mouza, dag), (None, None))[0],
            longitude=COORDS.get((mouza, dag), (None, None))[1],
        )
        plot.holdings.append(
            Holding(
                holder_name=owner,
                holder_norm=names.normalize_name(owner) or owner.lower(),
                area=Decimal(area),
                khatian_name=khatian_name,
            )
        )
        db.add(plot)
    db.commit()

    # Sample history so the ledger and QR codes are not empty on first run.
    sample = register_deed(
        db,
        DeedCreate(
            mouza="রহিমপুর", dag=414, seller="আনোয়ার হোসেন", buyer="নাসিমা খাতুন",
            area=Decimal("12"), deed_date=date(2025, 3, 12),
        ),
        signer,
    )
    complete_mutation(db, sample.deed_no)  # type: ignore[arg-type]

    register_deed(
        db,
        DeedCreate(
            mouza="শ্যামপুর", dag=56, seller="নাসরিন আক্তার", buyer="তানভীর আহমেদ",
            area=Decimal("5"), deed_date=date(2025, 8, 20),
        ),
        signer,
    )  # mutation intentionally left pending

    log.info("Demo data loaded")
    return True


if __name__ == "__main__":  # python -m app.seed [--reset]
    import sys

    from app.database import SessionLocal, init_db
    from app.deps import get_signer

    logging.basicConfig(level=logging.INFO)
    init_db()
    with SessionLocal() as session:
        if "--reset" in sys.argv:
            reset_data(session)
        print("seeded" if seed_demo(session, get_signer()) else "already has data (use --reset)")
