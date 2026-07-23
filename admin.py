"""
Accesso riservato al CREATORE del sito.

La password NON è scritta in chiaro nel codice (finirebbe leggibile su GitHub):
è salvata come impronta cifrata (hash scrypt). Il login funziona con la
password vera, ma dal codice non è recuperabile.

Per CAMBIARE la password senza toccare il codice: crea il file
`instance/admin_password.txt` e scrivici dentro la nuova password.
"""

import json
import secrets
import time

from werkzeug.security import check_password_hash, generate_password_hash

from config import INSTANCE_DIR

_RESET_FILE = INSTANCE_DIR / "admin_reset.json"
_RESET_TTL = 900  # il codice di reset vale 15 minuti

# Hash della password del creatore (scrypt). In chiaro non c'è.
_ADMIN_HASH = (
    "scrypt:32768:8:1$BgPqvK6HjfO1pORK$71e81521ddc25a0419c55a4ca48dd87b"
    "c1050c20b94a282466a0cc2d3af4edad8e35a01db4d51e3edc6b91bad82ac86712"
    "f1593883bf21e5fe9b77081a70d47e"
)

ADMIN_EMAIL = "creatore@vcriptov.local"


def check_admin_password(pw: str) -> bool:
    if not pw:
        return False
    override = INSTANCE_DIR / "admin_password.txt"
    if override.exists():
        stored = override.read_text(encoding="utf-8").strip()
        return bool(stored) and pw == stored
    return check_password_hash(_ADMIN_HASH, pw)


# ---- Recupero password via email (codice temporaneo) ----
def create_reset_code() -> str:
    """Genera un codice a 6 cifre, ne salva l'impronta con scadenza, lo ritorna."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    _RESET_FILE.write_text(json.dumps({
        "hash": generate_password_hash(code),
        "exp": time.time() + _RESET_TTL,
    }), encoding="utf-8")
    return code


def verify_reset_code(code: str) -> bool:
    if not code or not _RESET_FILE.exists():
        return False
    try:
        data = json.loads(_RESET_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False
    if time.time() > float(data.get("exp", 0)):
        return False
    return check_password_hash(data.get("hash", ""), code.strip())


def clear_reset_code() -> None:
    try:
        _RESET_FILE.unlink()
    except OSError:
        pass


def set_admin_password(new_pw: str) -> None:
    """Imposta la nuova password del creatore (scritta in instance/, non nel codice)."""
    (INSTANCE_DIR / "admin_password.txt").write_text(new_pw.strip(), encoding="utf-8")
