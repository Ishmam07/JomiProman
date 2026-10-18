"""Request / response models (these also drive the Swagger docs at /docs)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["GREEN", "AMBER", "RED"]


def _strip(value: str) -> str:
    return " ".join(value.split())


class _Named(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _strip_strings(cls, v: Any) -> Any:
        return _strip(v) if isinstance(v, str) else v


# ---------------------------------------------------------------- requests
class DeedCreate(_Named):
    mouza: str = Field(min_length=1, max_length=100, examples=["রহিমপুর"])
    dag: int = Field(gt=0, le=999999, examples=[412])
    seller: str = Field(min_length=2, max_length=120, examples=["করিম"])
    buyer: str = Field(min_length=2, max_length=120, examples=["রফিক"])
    area: Decimal = Field(gt=0, le=100000, max_digits=10, decimal_places=2, examples=[6])
    deed_date: date | None = None


class VerifyCopy(_Named):
    """Fields printed on a paper copy of a deed, to be checked against the ledger."""

    deed_no: str = Field(min_length=3, max_length=20, examples=["D-0002"])
    mouza: str = Field(min_length=1, max_length=100)
    dag: int = Field(gt=0, le=999999)
    seller: str = Field(min_length=2, max_length=120)
    buyer: str = Field(min_length=2, max_length=120)
    area: Decimal = Field(gt=0, le=100000, max_digits=10, decimal_places=2)
    deed_date: date
    hash: str | None = Field(default=None, max_length=64, description="Fingerprint from the QR code")


class LocationIn(_Named):
    latitude: float = Field(ge=-90, le=90, examples=[23.8103])
    longitude: float = Field(ge=-180, le=180, examples=[90.4125])
    address: str | None = Field(default=None, max_length=200)


class ExplainRequest(BaseModel):
    status: Severity
    findings: list[dict[str, Any]] = Field(default_factory=list, max_length=12)


class AskRequest(_Named):
    mouza: str = Field(min_length=1, max_length=100)
    dag: int = Field(gt=0, le=999999)
    question: str = Field(min_length=2, max_length=300)


class ExtractRequest(BaseModel):
    text: str = Field(min_length=5, max_length=4000)


# --------------------------------------------------------------- responses
class FindingOut(BaseModel):
    code: str
    severity: Severity
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class DeedOut(BaseModel):
    deed_no: str
    status: Literal["REGISTERED", "BLOCKED"]
    risk: Severity
    mouza: str
    dag: int
    seller: str
    buyer: str
    area: float
    deed_date: date
    fingerprint: str
    record_hash: str | None
    chain_index: int | None
    signature: str | None
    mutation_status: Literal["NA", "PENDING", "DONE"]
    findings: list[FindingOut]
    verify_url: str | None
    qr_image_url: str | None
    created_at: datetime


class CheckItem(BaseModel):
    key: str
    label: str
    ok: bool | None  # None -> could not be evaluated


class ChangeItem(BaseModel):
    field: str
    label: str
    stored: str
    provided: str


class VerifyResponse(BaseModel):
    status: Severity
    headline: str
    findings: list[FindingOut]
    checks: list[CheckItem]
    changes: list[ChangeItem]
    deed: DeedOut | None


class HoldingOut(BaseModel):
    holder: str
    area: float
    mutated: bool


class HistoryItem(BaseModel):
    deed_no: str
    status: str
    risk: Severity
    seller: str
    buyer: str
    area: float
    deed_date: date
    chain_index: int | None
    mutation_status: str


class ChainOut(BaseModel):
    valid: bool
    length: int
    broken_deed_no: str | None = None
    reason: str | None = None


class PlotView(BaseModel):
    mouza: str
    dag: int
    khatian_no: str | None
    land_type: str
    total_area: float
    status: Severity
    headline: str
    advice: str
    findings: list[FindingOut]
    holdings: list[HoldingOut]
    history: list[HistoryItem]
    chain: ChainOut
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None


class PlotListItem(BaseModel):
    mouza: str
    dag: int
    latitude: float | None = None
    longitude: float | None = None


class Stats(BaseModel):
    plots: int
    deeds_registered: int
    deeds_blocked: int
    deeds_need_attention: int
    cache_backend: str
    ai_enabled: bool


class AssistantReply(BaseModel):
    text: str
    source: Literal["ai", "template"]
    model: str | None = None


class ExtractedFields(BaseModel):
    mouza: str | None = None
    dag: int | None = None
    seller: str | None = None
    buyer: str | None = None
    area: float | None = None
    deed_date: date | None = None


class ExtractResponse(BaseModel):
    fields: ExtractedFields
    missing: list[str]
    source: Literal["ai", "template"]
    note: str
