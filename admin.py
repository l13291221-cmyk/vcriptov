"""
Accesso riservato al CREATORE del sito.

La password NON è scritta in chiaro nel codice (finirebbe leggibile su GitHub):
è salvata come impronta cifrata (hash scrypt). Il login funziona con la
password vera, ma dal codice non è recuperabile.

Per CAMBIARE la password senza toccare il codice: crea il file
`instance/admin_password.txt` e scrivici dentro la nuova password.
"""

from werkzeug.security import check_password_hash

from config import INSTANCE_DIR

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
