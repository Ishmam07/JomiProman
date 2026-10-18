"""End-to-end scenarios through the HTTP API (the same story as the demo video)."""

from sqlalchemy import select

from app.database import engine
from app.db_guards import drop_guards
from app.models import Deed
from tests.conftest import AUTH, codes, deed_body, register


# ------------------------------------------------------------------ basics
def test_health_and_stats(client):
    health = client.get("/api/health").json()
    assert health["status"] == "ok" and health["database"] == "up"
    assert health["cache"] == "memory" and health["ai"] == "fallback-mode"

    stats = client.get("/api/stats").json()
    assert stats["plots"] == 7
    assert stats["deeds_registered"] == 2  # two seeded sample transfers


def test_public_key_is_exposed(client):
    key = client.get("/api/public-key").json()
    assert key["algorithm"] == "Ed25519" and len(key["public_key_hex"]) == 64


def test_registering_requires_registrar_key(client):
    r = client.post("/api/deeds", json=deed_body())
    assert r.status_code == 401
    r = client.post("/api/deeds", json=deed_body(), headers={"X-Registrar-Key": "wrong"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_registrar_key"


def test_validation_errors_are_friendly(client):
    r = client.post("/api/deeds", json=deed_body(area=-1, dag=0), headers=AUTH)
    assert r.status_code == 422
    assert "জমির পরিমাণ" in r.json()["error"]["message"]


def test_unknown_plot_is_404(client):
    r = register(client, mouza="অজানা", dag=1)
    assert r.status_code == 404 and r.json()["error"]["code"] == "plot_not_found"


# --------------------------------------------- the double-sale demo story
def test_double_sale_story(client):
    # 1. Karim sells 6 of his 10 shatangsha to Rafiq: accepted, chained, signed.
    a = register(client, buyer="রফিক", area=6)
    assert a.status_code == 201
    a = a.json()
    assert a["status"] == "REGISTERED" and a["risk"] == "GREEN"
    assert a["chain_index"] == 1 and a["signature"] and a["qr_image_url"]
    assert a["verify_url"].endswith(f"/verify?deed={a['deed_no']}&hash={a['fingerprint']}")

    # 2. Karim now holds only 4. Selling 7 more is a double-sale: RED + blocked.
    b = register(client, buyer="সালমা", area=7).json()
    assert b["status"] == "BLOCKED" and b["risk"] == "RED"
    assert "AREA_EXCEEDS" in codes(b)
    assert b["findings"][0]["data"] == {"remaining": 4.0, "requested": 7.0}
    assert "৪ শতাংশ" in b["findings"][0]["message"] and "৭ শতাংশ" in b["findings"][0]["message"]
    assert b["signature"] is None and b["qr_image_url"] is None

    # 3. Land did not move for the blocked deed.
    plot = client.get("/api/plots/রহিমপুর/412").json()
    holders = {h["holder"]: h["area"] for h in plot["holdings"]}
    assert holders == {"করিম": 4.0, "রফিক": 6.0}

    # 4. A selling the same 4 again is fine; 4.01 is not.
    assert register(client, buyer="তানিয়া", area=4.01).json()["status"] == "BLOCKED"
    assert register(client, buyer="তানিয়া", area=4).json()["status"] == "REGISTERED"
    # ... and now Karim has nothing left.
    again = register(client, buyer="কেউ একজন", area=1).json()
    assert again["status"] == "BLOCKED" and "AREA_EXCEEDS" in codes(again)


def test_paper_copy_tampering_is_caught_with_exact_fields(client):
    a = register(client).json()
    copy = {
        "deed_no": a["deed_no"], "mouza": a["mouza"], "dag": a["dag"], "seller": a["seller"],
        "buyer": a["buyer"], "area": a["area"], "deed_date": a["deed_date"], "hash": a["fingerprint"],
    }
    ok = client.post("/api/verify", json=copy).json()
    assert ok["status"] == "GREEN"
    assert all(c["ok"] for c in ok["checks"])

    forged = client.post("/api/verify", json={**copy, "buyer": "জামাল"}).json()
    assert forged["status"] == "RED" and "DOC_ALTERED" in codes(forged)
    assert [c["field"] for c in forged["changes"]] == ["buyer"]
    assert forged["changes"][0]["stored"] == "রফিক" and forged["changes"][0]["provided"] == "জামাল"

    bigger = client.post("/api/verify", json={**copy, "area": 9}).json()
    assert bigger["status"] == "RED" and [c["field"] for c in bigger["changes"]] == ["area"]

    bad_hash = client.post("/api/verify", json={**copy, "hash": "0" * 64}).json()
    assert bad_hash["status"] == "RED" and "HASH_MISMATCH" in codes(bad_hash)


def test_qr_verification_flow(client):
    a = register(client).json()
    ok = client.get(f"/api/verify/{a['deed_no']}", params={"hash": a["fingerprint"]}).json()
    assert ok["status"] == "GREEN" and ok["deed"]["buyer"] == "রফিক"

    fake = client.get(f"/api/verify/{a['deed_no']}", params={"hash": "f" * 64}).json()
    assert fake["status"] == "RED" and "HASH_MISMATCH" in codes(fake)

    missing = client.get("/api/verify/D-9999").json()
    assert missing["status"] == "RED" and "DEED_NOT_FOUND" in codes(missing)

    # lowercase deed numbers are accepted
    assert client.get(f"/api/verify/{a['deed_no'].lower()}").json()["status"] == "GREEN"


def test_blocked_deed_never_verifies_as_genuine(client):
    register(client, area=6)
    blocked = register(client, buyer="সালমা", area=7).json()
    result = client.get(f"/api/verify/{blocked['deed_no']}", params={"hash": blocked["fingerprint"]}).json()
    assert result["status"] == "RED" and "DEED_BLOCKED" in codes(result)
    assert client.get(f"/api/deeds/{blocked['deed_no']}/qr").status_code == 404


def test_qr_png_for_registered_deed(client):
    a = register(client).json()
    r = client.get(a["qr_image_url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.content.startswith(b"\x89PNG")


# ------------------------------------------------------------- other rules
def test_seller_who_is_not_owner(client):
    d = register(client, seller="ফারুক").json()
    assert d["status"] == "BLOCKED" and "NOT_OWNER" in codes(d)


def test_self_sale_blocked(client):
    d = register(client, seller="করিম", buyer="মোঃ করিম").json()
    assert d["status"] == "BLOCKED" and "SELF_SALE" in codes(d)


def test_bank_lien_blocks_sale(client):
    d = register(client, dag=413, seller="সুলতানা বেগম", area=5).json()
    assert d["status"] == "BLOCKED" and "PLOT_BANK_LIEN" in codes(d)
    assert "জনতা ব্যাংক" in d["findings"][0]["message"]


def test_court_case_and_khas_block_sale(client):
    court = register(client, mouza="চন্দনপুর", dag=101, seller="জামাল উদ্দিন", area=2).json()
    assert court["status"] == "BLOCKED" and "PLOT_COURT_CASE" in codes(court)
    khas = register(client, mouza="শ্যামপুর", dag=55, seller="বাংলাদেশ সরকার", area=2).json()
    assert khas["status"] == "BLOCKED" and "PLOT_KHAS" in codes(khas)


def test_name_variants_are_amber_not_red(client):
    # Khatian says "আব্দুল হাক"; the deed says "আব্দুল হক" -> accepted with a warning.
    d = register(client, mouza="চন্দনপুর", dag=102, seller="আব্দুল হক", area=3).json()
    assert d["status"] == "REGISTERED" and d["risk"] == "AMBER"
    assert "KHATIAN_NAME_VARIANT" in codes(d)

    # Seller's own name spelled slightly differently from the holder -> amber too.
    d2 = register(client, seller="কারিম", buyer="রাকিব", area=1).json()
    assert d2["risk"] == "AMBER" and "NAME_MISMATCH" in codes(d2)


def test_pending_mutation_warns_until_completed(client):
    first = register(client, buyer="রফিক", area=6).json()
    assert first["mutation_status"] == "PENDING"

    # Rafiq resells before the khatian was updated -> amber
    resale = register(client, seller="রফিক", buyer="শামীম", area=2).json()
    assert resale["status"] == "REGISTERED" and "MUTATION_PENDING" in codes(resale)

    # Land office completes mutation (needs the registrar key)
    assert client.post(f"/api/deeds/{first['deed_no']}/mutation").status_code == 401
    done = client.post(f"/api/deeds/{first['deed_no']}/mutation", headers=AUTH).json()
    assert done["mutation_status"] == "DONE"
    assert client.post(f"/api/deeds/{first['deed_no']}/mutation", headers=AUTH).status_code == 409

    clean = register(client, seller="রফিক", buyer="হাসান", area=1).json()
    assert clean["risk"] == "GREEN"


# ------------------------------------------------------ check before you buy
def test_plot_check_views(client):
    clean = client.get("/api/plots/রহিমপুর/414").json()
    assert clean["status"] == "GREEN" and clean["chain"]["valid"]
    assert [h["holder"] for h in clean["holdings"]] == ["নাসিমা খাতুন"]

    lien = client.get("/api/plots/রহিমপুর/413").json()
    assert lien["status"] == "RED" and "PLOT_BANK_LIEN" in codes(lien)

    pending = client.get("/api/plots/শ্যামপুর/56").json()
    assert pending["status"] == "AMBER" and "MUTATION_PENDING" in codes(pending)

    assert client.get("/api/plots/রহিমপুর/9999").status_code == 404
    plots = client.get("/api/plots").json()
    assert any(p["mouza"] == "রহিমপুর" and p["dag"] == 412 for p in plots)


def test_plot_view_is_cached_and_invalidated_on_write(client):
    first = client.get("/api/plots/রহিমপুর/412").json()
    assert first["holdings"][0]["area"] == 10.0
    register(client, area=6)
    after = client.get("/api/plots/রহিমপুর/412").json()
    assert {h["holder"]: h["area"] for h in after["holdings"]} == {"করিম": 4.0, "রফিক": 6.0}


def test_flagged_list(client):
    register(client, area=6)
    blocked = register(client, buyer="সালমা", area=7).json()
    flagged = client.get("/api/deeds/flagged").json()
    assert blocked["deed_no"] in {d["deed_no"] for d in flagged}
    assert all(d["status"] == "BLOCKED" or d["risk"] == "AMBER" for d in flagged)


# ------------------------------------------------ ledger tamper detection
def test_tampering_with_the_database_is_detected(client, db):
    a = register(client).json()
    assert client.get("/api/plots/রহিমপুর/412/chain").json()["valid"] is True

    # An insider with DBA rights removes the triggers, then edits the buyer directly.
    drop_guards(engine)
    deed = db.execute(select(Deed).where(Deed.deed_no == a["deed_no"])).scalar_one()
    deed.buyer = "জালিয়াত"
    db.commit()

    chain = client.get("/api/plots/রহিমপুর/412/chain").json()
    assert chain["valid"] is False and chain["broken_deed_no"] == a["deed_no"]
    assert chain["reason"] == "RECORD_TAMPERED"

    result = client.get(f"/api/verify/{a['deed_no']}", params={"hash": a["fingerprint"]}).json()
    assert result["status"] == "RED" and "RECORD_TAMPERED" in codes(result)


def test_forged_signature_is_detected(client, db):
    a = register(client).json()
    drop_guards(engine)
    deed = db.execute(select(Deed).where(Deed.deed_no == a["deed_no"])).scalar_one()
    deed.signature = "ab" * 64
    db.commit()
    chain = client.get("/api/plots/রহিমপুর/412/chain").json()
    assert chain["valid"] is False and chain["reason"] == "SIGNATURE_INVALID"


def test_rewriting_history_breaks_later_links(client, db):
    register(client, buyer="রফিক", area=2)
    second = register(client, buyer="সালমা", area=2).json()
    drop_guards(engine)
    first = db.execute(select(Deed).where(Deed.chain_index == 1, Deed.plot_id == 1)).scalars().first()
    assert first is not None
    first.prev_hash = "0" * 64
    db.commit()
    chain = client.get("/api/plots/রহিমপুর/412/chain").json()
    assert chain["valid"] is False
    # the QR of a later deed is also affected because the chain before it is broken
    res = client.get(f"/api/verify/{second['deed_no']}", params={"hash": second["fingerprint"]}).json()
    assert res["status"] == "RED"


# ------------------------------------------------------------ map location
def test_plot_location_seeded_and_updatable(client):
    view = client.get("/api/plots/রহিমপুর/412").json()
    assert view["latitude"] == 23.8103 and view["longitude"] == 90.4125

    url = "/api/plots/রহিমপুর/412/location"
    body = {"latitude": 24.5, "longitude": 91.25, "address": "Test road"}
    assert client.put(url, json=body).status_code == 401  # registrar key required
    assert client.put(url, json={**body, "latitude": 123}, headers=AUTH).status_code == 422

    r = client.put(url, json=body, headers=AUTH)
    assert r.status_code == 200 and r.json()["latitude"] == 24.5
    again = client.get("/api/plots/রহিমপুর/412").json()  # cache must be invalidated
    assert again["longitude"] == 91.25 and again["address"] == "Test road"
    assert client.put("/api/plots/রহিমপুর/9999/location", json=body, headers=AUTH).status_code == 404
