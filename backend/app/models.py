"""Database tables.

Plot      one land parcel (mouza + dag number) and its legal flags
Holding   how much of the plot each person currently holds
Deed      every registration attempt; accepted deeds are chained and signed
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    Float,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

REGISTERED = "REGISTERED"
BLOCKED = "BLOCKED"


class Plot(Base):
    __tablename__ = "plots"
    __table_args__ = (UniqueConstraint("mouza", "dag", name="uq_plot_mouza_dag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    mouza: Mapped[str] = mapped_column(String(100), index=True)
    dag: Mapped[int] = mapped_column(Integer)
    khatian_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    land_type: Mapped[str] = mapped_column(String(40), default="কৃষি")
    total_area: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # shatangsha

    has_bank_lien: Mapped[bool] = mapped_column(Boolean, default=False)
    lien_bank: Mapped[str | None] = mapped_column(String(120), nullable=True)
    has_court_case: Mapped[bool] = mapped_column(Boolean, default=False)
    case_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_khas: Mapped[bool] = mapped_column(Boolean, default=False)

    # Optional map location (WGS84) so buyers can see the plot on Google Maps.
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="plot", cascade="all, delete-orphan", order_by="Holding.id"
    )
    deeds: Mapped[list["Deed"]] = relationship(
        back_populates="plot", cascade="all, delete-orphan", order_by="Deed.id"
    )


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("plot_id", "holder_norm", name="uq_holding_plot_holder"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plot_id: Mapped[int] = mapped_column(ForeignKey("plots.id", ondelete="CASCADE"), index=True)
    holder_name: Mapped[str] = mapped_column(String(120))
    holder_norm: Mapped[str] = mapped_column(String(120))
    area: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Name exactly as written in the khatian (land record). None => mutation pending.
    khatian_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    plot: Mapped[Plot] = relationship(back_populates="holdings")

    @property
    def mutated(self) -> bool:
        return self.khatian_name is not None


class Deed(Base):
    __tablename__ = "deeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    deed_no: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    plot_id: Mapped[int] = mapped_column(ForeignKey("plots.id", ondelete="CASCADE"), index=True)

    seller: Mapped[str] = mapped_column(String(120))
    buyer: Mapped[str] = mapped_column(String(120))
    area: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    deed_date: Mapped[date] = mapped_column(Date)

    status: Mapped[str] = mapped_column(String(12), index=True)  # REGISTERED | BLOCKED
    risk: Mapped[str] = mapped_column(String(8))  # GREEN | AMBER | RED
    findings: Mapped[list] = mapped_column(JSON, default=list)
    mutation_status: Mapped[str] = mapped_column(String(8), default="NA")  # NA | PENDING | DONE

    fingerprint: Mapped[str] = mapped_column(String(64), default="")
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chain_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signature: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    plot: Mapped[Plot] = relationship(back_populates="deeds")


class AuditEvent(Base):
    """Append-only style application activity log for administrator monitoring.

    The log intentionally stores summaries and field names, not raw deed text,
    admin/registrar secrets, or full AI prompts.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(32), default="public", index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), default="system", index=True)
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    outcome: Mapped[str] = mapped_column(String(24), default="ok", index=True)
    summary: Mapped[str] = mapped_column(String(255))
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
