"""Cryptography: deed fingerprints (SHA-256), hash-chain links and Ed25519 signatures."""

import base64
import hashlib
import json
import logging
import os
import re
import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.config import Settings

log = logging.getLogger(__name__)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_text(value: str) -> str:
    """Unicode-normalise and collapse whitespace so harmless spacing never changes a hash."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


def canonical_area(area: Decimal | float | str) -> str:
    return f"{Decimal(str(area)).quantize(Decimal('0.01')):.2f}"


def fingerprint(
    *,
    deed_no: str,
    mouza: str,
    dag: int,
    seller: str,
    buyer: str,
    area: Decimal | float | str,
    deed_date: date | str,
) -> str:
    """SHA-256 over the key fields of a deed. Any edit to any field changes the result."""
    payload = {
        "deed_no": clean_text(deed_no),
        "mouza": clean_text(mouza),
        "dag": int(dag),
        "seller": clean_text(seller),
        "buyer": clean_text(buyer),
        "area": canonical_area(area),
        "deed_date": deed_date.isoformat() if isinstance(deed_date, date) else str(deed_date),
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_hex(text)


def genesis_hash(mouza: str, dag: int) -> str:
    """Start of a plot's ledger chain."""
    return sha256_hex(f"GENESIS|{clean_text(mouza)}|{int(dag)}")


def link_hash(prev_hash: str, fp: str) -> str:
    """Each record commits to the one before it, so history cannot be rewritten silently."""
    return sha256_hex(f"{prev_hash}|{fp}")


class Signer:
    """Ed25519 signer used by the (simulated) sub-registrar."""

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._private = private_key
        self._public: Ed25519PublicKey = private_key.public_key()

    @classmethod
    def from_seed(cls, seed: bytes) -> "Signer":
        if len(seed) != 32:
            raise ValueError("Ed25519 seed must be exactly 32 bytes")
        return cls(Ed25519PrivateKey.from_private_bytes(seed))

    def sign(self, message_hex: str) -> str:
        return self._private.sign(message_hex.encode("ascii")).hex()

    def verify(self, message_hex: str, signature_hex: str | None) -> bool:
        if not signature_hex:
            return False
        try:
            self._public.verify(bytes.fromhex(signature_hex), message_hex.encode("ascii"))
            return True
        except (InvalidSignature, ValueError):
            return False

    @property
    def public_key_hex(self) -> str:
        raw = self._public.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return raw.hex()

    @property
    def key_id(self) -> str:
        return sha256_hex(self.public_key_hex)[:16]


def load_signer(settings: Settings) -> Signer:
    """Key priority: SIGNING_KEY_B64 env var -> key file -> generate and persist a new key."""
    if settings.signing_key_b64:
        return Signer.from_seed(base64.b64decode(settings.signing_key_b64))

    path = Path(settings.signing_key_path)
    if path.exists():
        return Signer.from_seed(base64.b64decode(path.read_text().strip()))

    seed = os.urandom(32)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(base64.b64encode(seed).decode())
        path.chmod(0o600)
        log.info("Generated a new signing key at %s", path)
    except OSError:
        log.warning("Could not persist signing key at %s; using an in-memory key", path)
    return Signer.from_seed(seed)
