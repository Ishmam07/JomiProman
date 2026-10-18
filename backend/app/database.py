"""SQLAlchemy engine, session factory and start-up helpers."""

import logging
import time
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

def _sqlalchemy_database_url(url: str) -> str:
    """Normalize Railway's mysql:// URL to the installed PyMySQL driver.

    Local Compose already supplies mysql+pymysql://. Railway's MYSQL_URL uses
    mysql://, which otherwise makes SQLAlchemy look for its default MySQL driver.
    """
    if url.startswith("mysql://"):
        return "mysql+pymysql://" + url[len("mysql://"):]
    return url


_connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(
    _sqlalchemy_database_url(settings.database_url),
    pool_pre_ping=True,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(retries: int = 30, delay: float = 2.0) -> None:
    """Create tables, waiting for the database container to accept connections."""
    from app import models  # noqa: F401  (register tables on Base.metadata)

    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            log.info("Database ready")
            _add_missing_columns()
            from app.db_guards import install_guards

            install_guards(engine)
            return
        except OperationalError as exc:
            log.warning("Database not ready (%s/%s): %s", attempt, retries, exc.orig)
            time.sleep(delay)
    raise RuntimeError("Database did not become ready in time")


def _add_missing_columns() -> None:
    """Tiny auto-migration so databases created before the map feature keep working."""
    from sqlalchemy import inspect, text

    cols = {c["name"] for c in inspect(engine).get_columns("plots")}
    wanted = {"latitude": "FLOAT", "longitude": "FLOAT", "address": "VARCHAR(200)"}
    with engine.begin() as conn:
        for name, ddl in wanted.items():
            if name not in cols:
                conn.execute(text(f"ALTER TABLE plots ADD COLUMN {name} {ddl} NULL"))
