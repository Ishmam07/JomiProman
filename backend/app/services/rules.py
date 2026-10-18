"""Deterministic fraud rules.

These rules (not the AI) decide GREEN / AMBER / RED. Every finding has a stable
`code`, a severity and a plain-Bangla message.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.bn import fmt_area
from app.models import Holding, Plot
from app.services import names

GREEN, AMBER, RED = "GREEN", "AMBER", "RED"
_ORDER = {GREEN: 0, AMBER: 1, RED: 2}


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "data": self.data,
        }


def worst(findings: list[Finding] | list[dict]) -> str:
    level = GREEN
    for f in findings:
        sev = f.severity if isinstance(f, Finding) else f["severity"]
        if _ORDER[sev] > _ORDER[level]:
            level = sev
    return level


@dataclass
class Evaluation:
    findings: list[Finding]
    seller_holding: Holding | None

    @property
    def risk(self) -> str:
        return worst(self.findings)


def plot_flag_findings(plot: Plot) -> list[Finding]:
    """Legal flags that attach to the plot itself, regardless of who is selling."""
    out: list[Finding] = []
    if plot.is_khas:
        out.append(
            Finding(
                "PLOT_KHAS",
                RED,
                "এটি খাস জমি হিসেবে চিহ্নিত; ব্যক্তিগত বিক্রি বৈধ নয়।",
            )
        )
    if plot.has_court_case:
        ref = f" ({plot.case_ref})" if plot.case_ref else ""
        out.append(
            Finding(
                "PLOT_COURT_CASE",
                RED,
                f"জমিটি নিয়ে মামলা চলমান{ref}; রায়ের আগে কেনাবেচা ঝুঁকিপূর্ণ।",
                {"case_ref": plot.case_ref},
            )
        )
    if plot.has_bank_lien:
        bank = plot.lien_bank or "একটি ব্যাংক"
        out.append(
            Finding(
                "PLOT_BANK_LIEN",
                RED,
                f"জমিটি {bank}-এর কাছে বন্ধক আছে; ব্যাংকের অনাপত্তি ছাড়া বিক্রি ঝুঁকিপূর্ণ।",
                {"bank": plot.lien_bank},
            )
        )
    return out


def find_holding(holdings: list[Holding], person: str) -> tuple[Holding | None, str]:
    """Match a name against the plot's holders. Returns (holding, SAME|SIMILAR|DIFFERENT)."""
    norm = names.normalize_name(person) or person.strip().lower()
    for h in holdings:
        if h.holder_norm == norm:
            return h, names.SAME

    best: tuple[Holding | None, str, int] = (None, names.DIFFERENT, 0)
    for h in holdings:
        label, score = names.classify(person, h.holder_name)
        if label != names.DIFFERENT and score > best[2]:
            best = (h, label, score)
    return best[0], best[1]


def evaluate_sale(
    plot: Plot,
    holdings: list[Holding],
    seller: str,
    buyer: str,
    area: Decimal,
) -> Evaluation:
    findings: list[Finding] = []

    if names.normalize_name(seller) == names.normalize_name(buyer):
        findings.append(Finding("SELF_SALE", RED, "বিক্রেতা ও ক্রেতা একই ব্যক্তি।"))

    findings.extend(plot_flag_findings(plot))

    holding, match = find_holding(holdings, seller)
    if holding is None:
        findings.append(
            Finding(
                "NOT_OWNER",
                RED,
                f"বিক্রেতা '{seller}' এই জমির বর্তমান মালিক নন।",
                {"seller": seller},
            )
        )
        return Evaluation(findings, None)

    if match == names.SIMILAR:
        findings.append(
            Finding(
                "NAME_MISMATCH",
                AMBER,
                f"বিক্রেতার নাম মালিকের নামের সাথে সামান্য অমিল ('{seller}' বনাম '{holding.holder_name}')।",
                {"seller": seller, "holder": holding.holder_name},
            )
        )

    remaining = Decimal(holding.area)
    if remaining <= 0:
        findings.append(
            Finding(
                "AREA_EXCEEDS",
                RED,
                "সম্ভাব্য দুইবার বিক্রি: বিক্রেতা এই জমির পুরো অংশ আগেই বিক্রি করেছেন।",
                {"remaining": 0.0, "requested": float(area)},
            )
        )
    elif area > remaining:
        findings.append(
            Finding(
                "AREA_EXCEEDS",
                RED,
                f"সম্ভাব্য দুইবার বিক্রি: বিক্রেতার হাতে আছে মাত্র {fmt_area(remaining)} শতাংশ, "
                f"কিন্তু {fmt_area(area)} শতাংশ বিক্রির চেষ্টা হয়েছে।",
                {"remaining": float(remaining), "requested": float(area)},
            )
        )

    if holding.khatian_name is None:
        findings.append(
            Finding(
                "MUTATION_PENDING",
                AMBER,
                "বিক্রেতার নামে নামজারি (মিউটেশন) এখনো সম্পন্ন হয়নি।",
            )
        )
    else:
        label, _ = names.classify(seller, holding.khatian_name)
        if label == names.SIMILAR:
            findings.append(
                Finding(
                    "KHATIAN_NAME_VARIANT",
                    AMBER,
                    f"খতিয়ানে নামের বানান ভিন্ন ('{holding.khatian_name}'); হাতে-কলমে মিলিয়ে নিন।",
                    {"khatian_name": holding.khatian_name},
                )
            )
        elif label == names.DIFFERENT:
            findings.append(
                Finding(
                    "KHATIAN_MISMATCH",
                    RED,
                    f"দলিলের নামের সাথে খতিয়ানের নাম ('{holding.khatian_name}') মেলে না।",
                    {"khatian_name": holding.khatian_name},
                )
            )

    return Evaluation(findings, holding)
