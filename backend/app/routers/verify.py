from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.deps import get_signer, rate_limit
from app.schemas import VerifyCopy, VerifyResponse
from app.security import Signer
from app.services import verification
from app.services.audit import record_event

router = APIRouter(prefix="/verify", tags=["Verification"], dependencies=[Depends(rate_limit("verify"))])


@router.post("", response_model=VerifyResponse, summary="Check a paper copy against the ledger")
def verify_paper_copy(
    payload: VerifyCopy,
    request: Request,
    db: Session = Depends(get_db),
    signer: Signer = Depends(get_signer),
    settings: Settings = Depends(get_settings),
):
    """Recomputes the SHA-256 fingerprint from the fields on the paper copy.
    If anything was edited, the fingerprint no longer matches and the result is RED,
    with the exact fields that differ."""
    result = verification.verify_copy(db, payload, signer, settings)
    record_event(
        db, request, action="verification.paper_copy", actor_type="public", entity_type="deed",
        entity_id=payload.deed_no, outcome=result["status"].lower(),
        summary=f"Paper-copy verification returned {result['status']}.",
        details={"status": result["status"], "changed_fields": [x.get("field") for x in result.get("changes", [])]},
    )
    return result


@router.get("/{deed_no}", response_model=VerifyResponse, summary="Verify via QR code")
def verify_qr(
    deed_no: str,
    request: Request,
    fp: str | None = Query(default=None, alias="hash", max_length=64),
    db: Session = Depends(get_db),
    signer: Signer = Depends(get_signer),
    settings: Settings = Depends(get_settings),
):
    result = verification.verify_qr(db, deed_no, fp, signer, settings)
    record_event(
        db, request, action="verification.qr", actor_type="public", entity_type="deed",
        entity_id=deed_no.strip().upper(), outcome=result["status"].lower(),
        summary=f"QR verification returned {result['status']}.",
        details={"status": result["status"]},
    )
    return result
