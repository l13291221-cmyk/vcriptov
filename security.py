"""
Cifratura simmetrica (Fernet / AES-128) per proteggere le credenziali
sensibili dell'utente salvate nel database: API key, API secret e token
Telegram non vengono mai salvati in chiaro.

La chiave di cifratura è generata al primo avvio e conservata in
`instance/fernet.key` con permessi 0600.
"""

import base64
import os

from cryptography.fernet import Fernet, InvalidToken

from config import load_or_create_secret

_fernet_instance: Fernet | None = None


def _fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        # SICUREZZA: se è impostata la variabile d'ambiente FERNET_KEY, la chiave
        # di cifratura sta SEPARATA dal database. Così, se un giorno trapelasse
        # solo il database, le credenziali resterebbero illeggibili.
        env_key = os.environ.get("FERNET_KEY")
        if env_key:
            key = env_key.strip().encode()
        else:
            key = base64.urlsafe_b64encode(load_or_create_secret("fernet.key", 32))
        _fernet_instance = Fernet(key)
    return _fernet_instance


def encrypt(text: str | None) -> str | None:
    """Cifra una stringa. Ritorna None se l'input è vuoto/None."""
    if not text:
        return None
    return _fernet().encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt(token: str | None) -> str:
    """Decifra una stringa. Ritorna '' in caso di token assente o non valido."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def mask(secret: str, visible: int = 4) -> str:
    """Restituisce una versione mascherata per mostrare a schermo (••••abcd)."""
    if not secret:
        return ""
    if len(secret) <= visible:
        return "•" * len(secret)
    return "•" * (len(secret) - visible) + secret[-visible:]
