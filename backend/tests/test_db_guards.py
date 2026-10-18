"""The database refuses to rewrite or delete signed deeds; the hash chain catches it if it is bypassed."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from app.database import engine
from app.db_guards import drop_guards, install_guards
from app.models import Deed
from app.services.ledger import verify_chain
from tests.conftest import AUTH, deed_body


@pytest.fixture()
def guarded(client):
    assert install_guards(engine)
    yield client
    drop_guards(engine)


def _register(client):
    res = client.post("/api/deeds", json=deed_body(), headers=AUTH)
    assert res.status_code == 201
    return res.json()["deed_no"]


def test_update_of_signed_deed_is_rejected(guarded):
    deed_no = _register(guarded)
    with pytest.raises(DatabaseError, match="append-only"):
        with engine.begin() as conn:
            conn.execute(text("UPDATE deeds SET buyer = 'জালিয়াত' WHERE deed_no = :n"), {"n": deed_no})


def test_delete_of_signed_deed_is_rejected(guarded):
    deed_no = _register(guarded)
    with pytest.raises(DatabaseError, match="append-only"):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM deeds WHERE deed_no = :n"), {"n": deed_no})


def test_workflow_column_can_still_change(guarded):
    deed_no = _register(guarded)
    res = guarded.post(f"/api/deeds/{deed_no}/mutation", headers=AUTH)
    assert res.status_code == 200 and res.json()["mutation_status"] == "DONE"


def test_blocked_attempts_are_still_logged_while_guarded(guarded):
    _register(guarded)
    res = guarded.post("/api/deeds", json=deed_body(buyer="সালমা", area=7), headers=AUTH)
    assert res.json()["status"] == "BLOCKED"


def test_bypassing_the_triggers_is_still_detected_by_the_chain(guarded, db):
    deed_no = _register(guarded)
    drop_guards(engine)  # attacker with DBA rights
    with engine.begin() as conn:
        conn.execute(text("UPDATE deeds SET buyer = 'জালিয়াত' WHERE deed_no = :n"), {"n": deed_no})
    db.expire_all()
    deed = db.query(Deed).filter_by(deed_no=deed_no).one()
    from app.deps import get_signer

    status = verify_chain(deed.plot, get_signer())
    assert status.valid is False and status.reason == "RECORD_TAMPERED"
