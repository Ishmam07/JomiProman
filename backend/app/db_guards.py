"""Database-level protection for the deed ledger.

Once a deed has been signed and chained (``record_hash`` is set) the database itself refuses to
change its legal fields or delete it, even for someone running raw SQL. Only workflow columns
(``mutation_status``) may still change.

This is defence in depth: a person with full DBA rights can still drop the triggers, which is why
every read also re-computes the hash chain and Ed25519 signatures (see ``services/ledger.py``).
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger(__name__)

UPDATE_TRIGGER = "trg_deeds_guard_update"
DELETE_TRIGGER = "trg_deeds_guard_delete"
MESSAGE = "Ledger is append-only: signed deed records cannot be changed or deleted"

# Columns that are frozen once the deed is signed.
_FROZEN = (
    "plot_id", "deed_no", "seller", "buyer", "area", "deed_date",
    "status", "fingerprint", "prev_hash", "record_hash", "chain_index", "signature",
)


def _mysql_statements() -> list[str]:
    same = " AND ".join(f"OLD.{c} <=> NEW.{c}" for c in _FROZEN)
    return [
        f"DROP TRIGGER IF EXISTS {UPDATE_TRIGGER}",
        f"DROP TRIGGER IF EXISTS {DELETE_TRIGGER}",
        (
            f"CREATE TRIGGER {UPDATE_TRIGGER} BEFORE UPDATE ON deeds FOR EACH ROW "
            f"BEGIN IF OLD.record_hash IS NOT NULL AND NOT ({same}) THEN "
            f"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{MESSAGE}'; END IF; END"
        ),
        (
            f"CREATE TRIGGER {DELETE_TRIGGER} BEFORE DELETE ON deeds FOR EACH ROW "
            f"BEGIN IF OLD.record_hash IS NOT NULL THEN "
            f"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{MESSAGE}'; END IF; END"
        ),
    ]


def _sqlite_statements() -> list[str]:
    changed = " OR ".join(f"OLD.{c} IS NOT NEW.{c}" for c in _FROZEN)
    return [
        f"DROP TRIGGER IF EXISTS {UPDATE_TRIGGER}",
        f"DROP TRIGGER IF EXISTS {DELETE_TRIGGER}",
        (
            f"CREATE TRIGGER {UPDATE_TRIGGER} BEFORE UPDATE ON deeds "
            f"WHEN OLD.record_hash IS NOT NULL AND ({changed}) "
            f"BEGIN SELECT RAISE(ABORT, '{MESSAGE}'); END"
        ),
        (
            f"CREATE TRIGGER {DELETE_TRIGGER} BEFORE DELETE ON deeds "
            f"WHEN OLD.record_hash IS NOT NULL "
            f"BEGIN SELECT RAISE(ABORT, '{MESSAGE}'); END"
        ),
    ]


def install_guards(engine: Engine) -> bool:
    """Create the append-only triggers. Returns False (and logs) if the DB refuses."""
    statements = _sqlite_statements() if engine.dialect.name == "sqlite" else _mysql_statements()
    try:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
    except SQLAlchemyError as exc:
        log.warning(
            "Could not install ledger triggers (%s). The hash chain still detects tampering. "
            "On MySQL with binary logging, start the server with --log-bin-trust-function-creators=1.",
            getattr(exc, "orig", exc),
        )
        return False
    log.info("Append-only ledger triggers installed")
    return True


def drop_guards(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"DROP TRIGGER IF EXISTS {UPDATE_TRIGGER}"))
        conn.execute(text(f"DROP TRIGGER IF EXISTS {DELETE_TRIGGER}"))
