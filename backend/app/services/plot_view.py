"""The "Check before you buy" view of a plot."""

from sqlalchemy.orm import Session

from app.bn import to_bn
from app.config import Settings
from app.models import REGISTERED
from app.security import Signer
from app.services.cache import Cache
from app.services.ledger import get_plot, verify_chain
from app.services.rules import AMBER, GREEN, RED, Finding, plot_flag_findings, worst

HEADLINES = {
    GREEN: "কোনো ঝুঁকি পাওয়া যায়নি",
    AMBER: "সতর্কতা: কিছু বিষয় যাচাই করুন",
    RED: "ঝুঁকিপূর্ণ: কেনার আগে থামুন",
}
ADVICE = {
    GREEN: "লেজারে কোনো জালিয়াতির চিহ্ন নেই। তবুও টাকা দেওয়ার আগে সাব-রেজিস্ট্রি অফিসে মূল দলিল ও খতিয়ান মিলিয়ে নিন।",
    AMBER: "নিচের সতর্কতাগুলো পরিষ্কার না হওয়া পর্যন্ত টাকা দেবেন না। ভূমি অফিস বা আইনজীবীর সাথে কথা বলুন।",
    RED: "এই জমি এখন কেনা ঝুঁকিপূর্ণ। সমস্যাগুলো মীমাংসা না হওয়া পর্যন্ত কোনো টাকা দেবেন না এবং আইনজীবীর পরামর্শ নিন।",
}
_CHAIN_MESSAGES = {
    "RECORD_TAMPERED": "লেজারের একটি রেকর্ড পরিবর্তিত হয়েছে।",
    "CHAIN_BROKEN": "মালিকানার শিকল ভাঙা পাওয়া গেছে।",
    "SIGNATURE_INVALID": "একটি দলিলের ডিজিটাল সই বৈধ নয়।",
}


def plot_cache_key(mouza: str, dag: int) -> str:
    return f"plot:{mouza}:{dag}"


def invalidate_plot(cache: Cache, mouza: str, dag: int) -> None:
    """Called after every write so buyers never see a stale plot."""
    cache.delete(plot_cache_key(mouza, dag))


def build_plot_view(db: Session, mouza: str, dag: int, signer: Signer) -> dict:
    plot = get_plot(db, mouza, dag)
    chain = verify_chain(plot, signer)

    findings: list[Finding] = plot_flag_findings(plot)
    if not chain.valid and chain.reason:
        findings.append(
            Finding(
                chain.reason,
                RED,
                f"{_CHAIN_MESSAGES[chain.reason]} ({chain.broken_deed_no})",
                {"broken_deed_no": chain.broken_deed_no},
            )
        )

    pending = [d for d in plot.deeds if d.status == REGISTERED and d.mutation_status == "PENDING"]
    if pending:
        findings.append(
            Finding(
                "MUTATION_PENDING",
                AMBER,
                f"{to_bn(len(pending))}টি হস্তান্তরের নামজারি এখনো বাকি; খতিয়ানে নতুন মালিকের নাম নেই।",
                {"deeds": [d.deed_no for d in pending]},
            )
        )

    blocked = [d for d in plot.deeds if d.status != REGISTERED]
    if blocked:
        findings.append(
            Finding(
                "BLOCKED_ATTEMPTS",
                AMBER,
                f"এই জমির {to_bn(len(blocked))}টি দলিল সন্দেহজনক হিসেবে আটকানো হয়েছে।",
                {"deeds": [d.deed_no for d in blocked]},
            )
        )

    status = worst(findings)
    return {
        "mouza": plot.mouza,
        "dag": plot.dag,
        "khatian_no": plot.khatian_no,
        "land_type": plot.land_type,
        "total_area": float(plot.total_area),
        "status": status,
        "headline": HEADLINES[status],
        "advice": ADVICE[status],
        "findings": [f.to_dict() for f in findings],
        "holdings": [
            {"holder": h.holder_name, "area": float(h.area), "mutated": h.mutated}
            for h in plot.holdings
            if float(h.area) > 0
        ],
        "history": [
            {
                "deed_no": d.deed_no,
                "status": d.status,
                "risk": d.risk,
                "seller": d.seller,
                "buyer": d.buyer,
                "area": float(d.area),
                "deed_date": d.deed_date,
                "chain_index": d.chain_index,
                "mutation_status": d.mutation_status,
            }
            for d in plot.deeds
        ],
        "chain": chain.to_dict(),
        "latitude": plot.latitude,
        "longitude": plot.longitude,
        "address": plot.address,
    }


def get_plot_view(
    db: Session, cache: Cache, settings: Settings, signer: Signer, mouza: str, dag: int
) -> dict:
    key = plot_cache_key(mouza, dag)
    cached = cache.get_json(key)
    if cached is not None:
        return cached
    view = build_plot_view(db, mouza, dag, signer)
    cache.set_json(key, view, settings.plot_cache_ttl)
    return view
