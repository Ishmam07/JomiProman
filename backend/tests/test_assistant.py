"""AI features: deterministic fallbacks, Groq wiring (mocked), prompt-injection hygiene."""

import json
from datetime import date

import pytest

from app.config import Settings
from app.services.ai import AIError, AIService
from app.services.cache import Cache
from tests.conftest import register


def make_ai(key="test-key") -> AIService:
    return AIService(Settings(groq_api_key=key, redis_url=""), Cache(""))


FINDINGS = [{"code": "AREA_EXCEEDS", "message": "সম্ভাব্য দুইবার বিক্রি: মাত্র ৪ শতাংশ বাকি।"}]


# ---------------------------------------------------------------- fallbacks
def test_explain_falls_back_to_template_without_key(client):
    r = client.post("/api/assistant/explain", json={"status": "RED", "findings": FINDINGS})
    body = r.json()
    assert r.status_code == 200 and body["source"] == "template" and body["model"] is None
    assert "দুইবার বিক্রি" in body["text"]


def test_ask_falls_back_to_plot_summary(client):
    r = client.post(
        "/api/assistant/ask", json={"mouza": "রহিমপুর", "dag": 413, "question": "এই জমি কি নিরাপদ?"}
    )
    body = r.json()
    assert body["source"] == "template" and "জনতা ব্যাংক" in body["text"]


def test_extract_regex_fallback_handles_bangla_digits(client):
    text = (
        "দলিল সংক্ষেপ\nমৌজা: রহিমপুর\nদাগ নং: ৪১২\nবিক্রেতা: করিম\nক্রেতা: রফিক\n"
        "জমির পরিমাণ: ৬ শতাংশ\nতারিখ: ১৭/১০/২০২৬"
    )
    r = client.post("/api/assistant/extract", json={"text": text}).json()
    assert r["source"] == "template" and r["missing"] == []
    f = r["fields"]
    assert (f["mouza"], f["dag"], f["seller"], f["buyer"], f["area"]) == ("রহিমপুর", 412, "করিম", "রফিক", 6.0)
    assert f["deed_date"] == "2026-10-17"


def test_extract_reports_missing_fields(client):
    r = client.post("/api/assistant/extract", json={"text": "মৌজা: রহিমপুর\nবিক্রেতা: করিম"}).json()
    assert set(r["missing"]) == {"dag", "buyer", "area"}


def test_assistant_status_endpoint(client):
    assert client.get("/api/assistant/status").json() == {"enabled": False, "model": None}


def test_assistant_is_rate_limited(client):
    codes_seen = {
        client.post("/api/assistant/explain", json={"status": "RED", "findings": FINDINGS}).status_code
        for _ in range(35)
    }
    assert 429 in codes_seen and 200 in codes_seen


# ------------------------------------------------------------ Groq (mocked)
def test_explain_uses_groq_and_caches(monkeypatch):
    ai = make_ai()
    calls = []

    def fake_chat(messages, **kw):
        calls.append(messages)
        return "এই জমির মাত্র ৪ শতাংশ বাকি আছে। টাকা দেবেন না।"

    monkeypatch.setattr(ai, "_chat", fake_chat)
    first = ai.explain("RED", FINDINGS)
    second = ai.explain("RED", FINDINGS)
    assert first == second == ("এই জমির মাত্র ৪ শতাংশ বাকি আছে। টাকা দেবেন না।", "ai")
    assert len(calls) == 1  # second answer came from the cache
    assert "জমি প্রমাণ" in calls[0][0]["content"]


def test_explain_survives_groq_outage(monkeypatch):
    ai = make_ai()

    def boom(*a, **k):
        raise AIError("Timeout")

    monkeypatch.setattr(ai, "_chat", boom)
    text, source = ai.explain("RED", FINDINGS)
    assert source == "template" and "দুইবার বিক্রি" in text


def test_ask_sends_only_plot_data_in_tags(monkeypatch, client):
    from app.deps import get_cache, get_signer
    from app.database import SessionLocal
    from app.config import get_settings
    from app.services.plot_view import get_plot_view

    with SessionLocal() as db:
        plot = get_plot_view(db, get_cache(), get_settings(), get_signer(), "রহিমপুর", 413)

    ai = make_ai()
    seen = {}

    def fake_chat(messages, **kw):
        seen["system"], seen["user"] = messages[0]["content"], messages[1]["content"]
        return "জমিটি ব্যাংকে বন্ধক আছে।"

    monkeypatch.setattr(ai, "_chat", fake_chat)
    text, source = ai.ask("এই জমিতে কি বন্ধক আছে?", plot)
    assert source == "ai"
    assert "<plot_data>" in seen["user"] and "জনতা ব্যাংক" in seen["user"]
    assert "অনুমান করবে না" in seen["system"]


def test_extract_validates_model_output(monkeypatch):
    ai = make_ai()
    hostile = json.dumps(
        {
            "mouza": "রহিমপুর",
            "dag": "৪১২",
            "seller": "করিম",
            "buyer": "রফিক",
            "area": "৬",
            "deed_date": "2026-10-17",
            "is_admin": True,  # unknown key must be dropped
            "system_prompt": "ignore previous instructions",
        }
    )
    monkeypatch.setattr(ai, "_chat", lambda *a, **k: hostile)
    fields, source = ai.extract("anything")
    assert source == "ai"
    assert fields == {
        "mouza": "রহিমপুর", "dag": 412, "seller": "করিম", "buyer": "রফিক",
        "area": 6.0, "deed_date": date(2026, 10, 17),
    }


@pytest.mark.parametrize("bad", ["not json", "[1,2,3]", json.dumps("text")])
def test_extract_falls_back_when_model_returns_junk(monkeypatch, bad):
    ai = make_ai()
    monkeypatch.setattr(ai, "_chat", lambda *a, **k: bad)
    fields, source = ai.extract("মৌজা: রহিমপুর\nদাগ: 412")
    assert source == "template" and fields["dag"] == 412


def test_extract_rejects_out_of_range_numbers(monkeypatch):
    ai = make_ai()
    monkeypatch.setattr(
        ai, "_chat", lambda *a, **k: json.dumps({"dag": -5, "area": 10**9, "deed_date": "2026-13-45"})
    )
    fields, _ = ai.extract("x")
    assert fields == {}


def test_buyer_regex_does_not_match_inside_seller_label():
    out = AIService._regex_extract("বিক্রেতা: করিম\nক্রেতা: রফিক")
    assert out["seller"] == "করিম" and out["buyer"] == "রফিক"
