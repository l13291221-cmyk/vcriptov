"""
Generazione e validazione dei codici di attivazione (license key).

Formato del codice:  PREFISSO-XXXX-XXXX-XXXX-CCCC
  - PREFISSO  = piano (STRT / PRO / VIP / LIFE)
  - XXXX...   = parte casuale (base32)
  - CCCC      = checksum HMAC-SHA256 (troncato) su email+piano+parte casuale,
                così un codice non può essere "inventato" senza la chiave segreta.

Il codice è comunque salvato nel database e considerato valido SOLO per il
livello di accesso (piano) con cui è stato emesso.
"""

import base64
import hashlib
import hmac
import secrets

from config import Config

_PLAN_PREFIX = {
    "starter": "STRT",
    "pro": "PRO",
    "vip": "VIP",
    "lifetime": "LIFE",
}

_ALPHABET = "ABCDEFGHIJKLMNPQRSTUVWXYZ23456789"  # base32 senza caratteri ambigui


def _b32(data: bytes) -> str:
    num = int.from_bytes(data, "big")
    out = ""
    while num > 0:
        num, rem = divmod(num, 32)
        out = _ALPHABET[rem] + out
    return out or _ALPHABET[0]


def _checksum(email: str, plan: str, random_part: str) -> str:
    msg = f"{email.strip().lower()}|{plan}|{random_part}".encode("utf-8")
    digest = hmac.new(Config.LICENSE_SIGNING_KEY, msg, hashlib.sha256).digest()
    return _b32(digest)[:4]


def generate_key(email: str, plan: str) -> str:
    """Genera un nuovo codice di attivazione legato a email + piano."""
    prefix = _PLAN_PREFIX.get(plan, "KEY")
    random_part = _b32(secrets.token_bytes(8))[:12].ljust(12, _ALPHABET[0])
    chunks = [random_part[0:4], random_part[4:8], random_part[8:12]]
    checksum = _checksum(email, plan, random_part)
    return "-".join([prefix] + chunks + [checksum])


def verify_checksum(email: str, plan: str, key: str) -> bool:
    """Verifica che il checksum del codice corrisponda a email + piano."""
    try:
        parts = key.strip().upper().split("-")
        if len(parts) != 5:
            return False
        random_part = parts[1] + parts[2] + parts[3]
        expected = _checksum(email, plan, random_part)
        return hmac.compare_digest(expected, parts[4])
    except Exception:
        return False


def normalize(key: str) -> str:
    return key.strip().upper()
