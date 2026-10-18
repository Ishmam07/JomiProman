"""Small Bangla formatting helpers."""

from decimal import Decimal

_TO_BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
_TO_EN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def to_bn(value: object) -> str:
    """Convert ASCII digits to Bangla digits."""
    return str(value).translate(_TO_BN)


def to_en(value: str) -> str:
    """Convert Bangla digits to ASCII digits."""
    return value.translate(_TO_EN)


def fmt_area(value: Decimal | float | int) -> str:
    """6.00 -> '৬', 4.5 -> '৪.৫' (Bangla digits, no trailing zeros)."""
    text = f"{Decimal(str(value)):f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return to_bn(text or "0")
