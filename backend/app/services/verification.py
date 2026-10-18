"""Verify a deed: paper-copy comparison and QR-code lookup."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bn import fmt_area
from app.config import Settings
from app.models import BLOCKED, Deed
from app.schemas import VerifyCopy
from app.security import Signer, fingerprint
from app.services.ledger import verify_chain
from app.services.rules import AMBER, GREEN, RED, Finding, plot_flag_findings, worst
from app.services.serializers import deed_to_dict

HEADLINES = {
    GREEN: "দলিলটি আসল ও অক্ষত",
    AMBER: "সতর্কতা: যাচাই করে এগোন",
    RED: "ঝুঁকি: দলিলটি বিশ্বাসযোগ্য নয়",
}

FIELD_LABELS = {
    "mouza": "মৌজা",
    "dag": "দাগ নম্বর",
    "seller": "বিক্রেতা",
    "buyer": "ক্রেতা",
    "area": "জমির পরিমাণ (শতাংশ)",
    "deed_date": "দলিলের তারিখ",
}

_CHAIN_MESSAGES = {
    "RECORD_TAMPERED": "লেজারের রেকর্ড পরিবর্তিত হয়েছে: সংরক্ষিত তথ্য ও ফিঙ্গারপ্রিন্ট মেলে না।",
    "CHAIN_BROKEN": "মালিকানার শিকল ভাঙা: আগের রেকর্ডের সাথে সংযোগ মেলে না।",
    "SIGNATURE_INVALID": "সাব-রেজিস্ট্রারের ডিজিটাল সই বৈধ নয়।",
}


def _not_found(deed_no: str) -> dict:
    finding = Finding(
        "DEED_NOT_FOUND",
        RED,
        f"দলিল নম্বর '{deed_no}' আমাদের লেজারে পাওয়া যায়নি; জাল হওয়ার সম্ভাবনা আছে।",
    )
    return {
        "status": RED,
        "headline": HEADLINES[RED],
        "findings": [finding.to_dict()],
        "checks": [],
        "changes": [],
        "deed": None,
    }


def _assess(
    db: Session,
    deed: Deed,
    signer: Signer,
    settings: Settings,
    extra: list[Finding],
    changes: list[dict],
) -> dict:
    findings = list(extra)
    plot = deed.plot

    blocked = deed.status == BLOCKED
    if blocked:
        findings.append(
            Finding(
                "DEED_BLOCKED",
                RED,
                "এই দলিলটি জালিয়াতি-যাচাইয়ে আটকানো হয়েছে; এটি বৈধ রেজিস্ট্রি নয়।",
                {"reasons": [f["code"] for f in (deed.findings or [])]},
            )
        )

    chain_ok: bool | None = None
    sig_ok: bool | None = None
    if not blocked:
        chain = verify_chain(plot, signer)
        affects_this = (not chain.valid) and (
            chain.broken_deed_no == deed.deed_no
            or (chain.broken_index or 0) <= (deed.chain_index or 0)
        )
        chain_ok = not affects_this
        sig_ok = not (affects_this and chain.reason == "SIGNATURE_INVALID")
        if affects_this and chain.reason:
            findings.append(
                Finding(
                    chain.reason,
                    RED,
                    _CHAIN_MESSAGES[chain.reason],
                    {"broken_deed_no": chain.broken_deed_no},
                )
            )

    plot_findings = plot_flag_findings(plot)
    findings.extend(plot_findings)

    fp_match = not any(f.code in ("DOC_ALTERED", "HASH_MISMATCH", "RECORD_TAMPERED") for f in findings)
    status = worst(findings)
    checks = [
        {"key": "fingerprint", "label": "ফিঙ্গারপ্রিন্ট (SHA-256) মিলেছে", "ok": fp_match and not blocked},
        {"key": "signature", "label": "সাব-রেজিস্ট্রারের ডিজিটাল সই বৈধ", "ok": sig_ok},
        {"key": "chain", "label": "মালিকানার শিকল অক্ষত", "ok": chain_ok},
        {"key": "plot_clear", "label": "জমিতে বন্ধক, মামলা বা খাস চিহ্ন নেই", "ok": not plot_findings},
    ]
    headline = HEADLINES[status]
    if any(f.code == "DOC_ALTERED" for f in findings):
        headline = "দলিল পরিবর্তিত: জাল হওয়ার সম্ভাবনা"
    return {
        "status": status,
        "headline": headline,
        "findings": [f.to_dict() for f in findings],
        "checks": checks,
        "changes": changes,
        "deed": deed_to_dict(deed, settings),
    }


def _find_deed(db: Session, deed_no: str) -> Deed | None:
    return db.execute(select(Deed).where(Deed.deed_no == deed_no.strip().upper())).scalar_one_or_none()


def _stored_values(deed: Deed) -> dict[str, str]:
    return {
        "mouza": deed.plot.mouza,
        "dag": str(deed.plot.dag),
        "seller": deed.seller,
        "buyer": deed.buyer,
        "area": fmt_area(deed.area),
        "deed_date": deed.deed_date.isoformat(),
    }


def verify_copy(db: Session, payload: VerifyCopy, signer: Signer, settings: Settings) -> dict:
    """Check a paper copy: recompute its fingerprint and compare with the ledger."""
    deed = _find_deed(db, payload.deed_no)
    if deed is None:
        return _not_found(payload.deed_no)

    provided_fp = fingerprint(
        deed_no=deed.deed_no or "",
        mouza=payload.mouza,
        dag=payload.dag,
        seller=payload.seller,
        buyer=payload.buyer,
        area=payload.area,
        deed_date=payload.deed_date,
    )

    extra: list[Finding] = []
    changes: list[dict] = []
    if provided_fp != deed.fingerprint:
        stored = _stored_values(deed)
        provided = {
            "mouza": payload.mouza,
            "dag": str(payload.dag),
            "seller": payload.seller,
            "buyer": payload.buyer,
            "area": fmt_area(payload.area),
            "deed_date": payload.deed_date.isoformat(),
        }
        for key, label in FIELD_LABELS.items():
            if " ".join(stored[key].split()) != " ".join(provided[key].split()):
                changes.append(
                    {"field": key, "label": label, "stored": stored[key], "provided": provided[key]}
                )
        names = "، ".join(c["label"] for c in changes) or "কিছু তথ্য"
        extra.append(
            Finding(
                "DOC_ALTERED",
                RED,
                f"কাগজের কপির তথ্য লেজারের সাথে মেলে না (পরিবর্তিত: {names})।",
                {"fields": [c["field"] for c in changes]},
            )
        )

    if payload.hash and payload.hash.strip().lower() != deed.fingerprint:
        extra.append(
            Finding("HASH_MISMATCH", RED, "QR কোডের ফিঙ্গারপ্রিন্ট লেজারের সাথে মেলে না।")
        )

    return _assess(db, deed, signer, settings, extra, changes)


def verify_qr(db: Session, deed_no: str, fp: str | None, signer: Signer, settings: Settings) -> dict:
    """QR flow: the QR carries the deed number and fingerprint."""
    deed = _find_deed(db, deed_no)
    if deed is None:
        return _not_found(deed_no)
    extra: list[Finding] = []
    if fp and fp.strip().lower() != deed.fingerprint:
        extra.append(
            Finding("HASH_MISMATCH", RED, "QR কোডের ফিঙ্গারপ্রিন্ট লেজারের সাথে মেলে না; QR জাল হতে পারে।")
        )
    return _assess(db, deed, signer, settings, extra, [])
