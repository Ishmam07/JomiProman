"""Turn ORM objects into response dictionaries."""

from app.config import Settings
from app.models import REGISTERED, Deed


def verify_url(settings: Settings, deed: Deed) -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/verify?deed={deed.deed_no}&hash={deed.fingerprint}"


def deed_to_dict(deed: Deed, settings: Settings) -> dict:
    registered = deed.status == REGISTERED
    return {
        "deed_no": deed.deed_no,
        "status": deed.status,
        "risk": deed.risk,
        "mouza": deed.plot.mouza,
        "dag": deed.plot.dag,
        "seller": deed.seller,
        "buyer": deed.buyer,
        "area": float(deed.area),
        "deed_date": deed.deed_date,
        "fingerprint": deed.fingerprint,
        "record_hash": deed.record_hash,
        "chain_index": deed.chain_index,
        "signature": deed.signature,
        "mutation_status": deed.mutation_status,
        "findings": deed.findings or [],
        "verify_url": verify_url(settings, deed) if registered else None,
        "qr_image_url": f"/api/deeds/{deed.deed_no}/qr" if registered else None,
        "created_at": deed.created_at,
    }
