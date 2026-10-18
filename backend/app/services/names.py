"""Fuzzy matching for Bangla person names.

The same person is often written differently on different papers
(করিম / কারিম / করীম, "মোঃ আব্দুল করিম" / "আবদুল করিম").
We normalise common variants, then compare with a fuzzy ratio.

Limitation: cross-script matching (Karim vs করিম) is not attempted.
"""

import re
import unicodedata

from rapidfuzz import fuzz

SAME = "SAME"
SIMILAR = "SIMILAR"
DIFFERENT = "DIFFERENT"

SAME_THRESHOLD = 97
SIMILAR_THRESHOLD = 80

_CHAR_FOLD = str.maketrans(
    {
        "ী": "ি",
        "ূ": "ু",
        "ঈ": "ই",
        "ঊ": "উ",
        "ণ": "ন",
        "শ": "স",
        "ষ": "স",
        "ঁ": "",
        "্": "",  # hasanta: আব্দুল == আবদুল
        "‌": "",
        "‍": "",
        "়": "",  # nukta left over after the replacements below
    }
)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    # NFC splits these into base letter + nukta
    text = text.replace("ড়", "র").replace("ঢ়", "ঢ").replace("য়", "য")
    return text.translate(_CHAR_FOLD)


_HONORIFICS = {
    _fold(w)
    for w in (
        "মো",
        "মোহাম্মদ",
        "মোহাম্মাদ",
        "মুহাম্মদ",
        "মুহাম্মাদ",
        "md",
        "mohammad",
        "muhammad",
        "mohammed",
    )
}


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFC", name).lower()
    text = re.sub(r"[.,:;ঃ()\-_/]", " ", text)
    tokens = [_fold(t) for t in text.split()]
    tokens = [t for t in tokens if t and t not in _HONORIFICS]
    return " ".join(tokens)


def classify(a: str, b: str) -> tuple[str, int]:
    """Return (SAME | SIMILAR | DIFFERENT, score 0-100)."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return DIFFERENT, 0
    if na == nb:
        return SAME, 100
    score = int(round(fuzz.token_sort_ratio(na, nb)))
    if score >= SAME_THRESHOLD:
        return SAME, score
    if score >= SIMILAR_THRESHOLD:
        return SIMILAR, score
    return DIFFERENT, score
