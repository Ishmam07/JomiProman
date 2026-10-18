from datetime import date
from decimal import Decimal

from app.security import (
    Signer,
    canonical_area,
    fingerprint,
    genesis_hash,
    link_hash,
    sha256_hex,
)

BASE = dict(
    deed_no="D-0001", mouza="রহিমপুর", dag=412, seller="করিম",
    buyer="রফিক", area=Decimal("6"), deed_date=date(2026, 10, 17),
)


def test_sha256_known_vector():
    assert sha256_hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_fingerprint_is_deterministic_and_ignores_whitespace():
    assert fingerprint(**BASE) == fingerprint(**BASE)
    spaced = {**BASE, "seller": "  করিম ", "mouza": "রহিমপুর  "}
    assert fingerprint(**spaced) == fingerprint(**BASE)


def test_fingerprint_area_formatting_does_not_matter():
    assert canonical_area(6) == canonical_area("6.0") == canonical_area(Decimal("6.00")) == "6.00"
    assert fingerprint(**{**BASE, "area": "6.0"}) == fingerprint(**BASE)


def test_any_field_change_changes_fingerprint():
    original = fingerprint(**BASE)
    for key, value in [
        ("buyer", "জামাল"),
        ("seller", "রহিম"),
        ("area", Decimal("7")),
        ("dag", 413),
        ("mouza", "চন্দনপুর"),
        ("deed_date", date(2026, 10, 18)),
        ("deed_no", "D-0002"),
    ]:
        assert fingerprint(**{**BASE, key: value}) != original, key


def test_chain_links_depend_on_previous_hash():
    g = genesis_hash("রহিমপুর", 412)
    fp = fingerprint(**BASE)
    assert link_hash(g, fp) != link_hash(sha256_hex("other"), fp)
    assert genesis_hash("রহিমপুর", 412) != genesis_hash("রহিমপুর", 413)


def test_signature_roundtrip_and_tamper_detection():
    signer = Signer.from_seed(bytes(range(32)))
    msg = sha256_hex("record")
    sig = signer.sign(msg)
    assert signer.verify(msg, sig)
    assert not signer.verify(sha256_hex("changed"), sig)
    assert not signer.verify(msg, "00" * 64)
    assert not signer.verify(msg, None)
    assert not signer.verify(msg, "not-hex")

    other = Signer.from_seed(bytes(reversed(range(32))))
    assert not other.verify(msg, sig)
