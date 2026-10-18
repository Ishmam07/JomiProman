from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.deps import get_ai, get_cache, get_signer, rate_limit
from app.schemas import (
    AskRequest,
    AssistantReply,
    ExplainRequest,
    ExtractRequest,
    ExtractResponse,
)
from app.security import Signer
from app.services.ai import AIService
from app.services.audit import record_event
from app.services.cache import Cache
from app.services.plot_view import get_plot_view

router = APIRouter(
    prefix="/assistant",
    tags=["AI assistant (Groq)"],
    dependencies=[Depends(rate_limit("assistant"))],
)

REQUIRED_FIELDS = ("mouza", "dag", "seller", "buyer", "area")


def _source_model(ai: AIService, source: str) -> str | None:
    return ai.model if source == "ai" else None


@router.get("/status", summary="Is the AI assistant configured?")
def status(ai: AIService = Depends(get_ai)):
    return {"enabled": ai.enabled, "model": ai.model if ai.enabled else None}


@router.post("/explain", response_model=AssistantReply, summary="Explain a verification result in simple Bangla")
def explain(req: ExplainRequest, request: Request, db: Session = Depends(get_db), ai: AIService = Depends(get_ai)):
    text, source = ai.explain(req.status, req.findings)
    record_event(db, request, action="assistant.explain", actor_type="public", entity_type="assistant",
                 outcome="ok", summary=f"AI explanation requested for {req.status} result.",
                 details={"source": source, "model": _source_model(ai, source), "finding_count": len(req.findings)})
    return {"text": text, "source": source, "model": _source_model(ai, source)}


@router.post("/ask", response_model=AssistantReply, summary="Ask a question about one plot")
def ask(
    req: AskRequest,
    request: Request,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    signer: Signer = Depends(get_signer),
    settings: Settings = Depends(get_settings),
    ai: AIService = Depends(get_ai),
):
    """Answers only from the plot's ledger data. Falls back to a plain summary without an API key."""
    plot = get_plot_view(db, cache, settings, signer, req.mouza, req.dag)
    text, source = ai.ask(req.question, plot)
    record_event(db, request, action="assistant.plot_question", actor_type="public", entity_type="plot",
                 entity_id=f"{req.mouza}/{req.dag}", outcome="ok",
                 summary=f"Plot question answered for {req.mouza}/{req.dag}.",
                 details={"source": source, "model": _source_model(ai, source), "question_length": len(req.question)})
    return {"text": text, "source": source, "model": _source_model(ai, source)}


@router.post("/extract", response_model=ExtractResponse, summary="Pre-fill the registration form from deed text")
def extract(req: ExtractRequest, request: Request, db: Session = Depends(get_db), ai: AIService = Depends(get_ai)):
    """Suggestions only: a human reviews the fields and the fraud rules still run on submit."""
    fields, source = ai.extract(req.text)
    missing = [k for k in REQUIRED_FIELDS if fields.get(k) in (None, "")]
    note = (
        "AI দিয়ে তথ্য নেওয়া হয়েছে; জমা দেওয়ার আগে নিজে মিলিয়ে নিন।"
        if source == "ai"
        else "সাধারণ প্যাটার্ন দিয়ে তথ্য নেওয়া হয়েছে (AI বন্ধ বা অনুপলব্ধ); জমা দেওয়ার আগে মিলিয়ে নিন।"
    )
    record_event(db, request, action="assistant.deed_extract", actor_type="public", entity_type="assistant",
                 outcome="ok", summary="Deed-text extraction completed; no raw deed text stored.",
                 details={"source": source, "model": _source_model(ai, source), "text_length": len(req.text), "missing_fields": missing})
    return {"fields": fields, "missing": missing, "source": source, "note": note}
