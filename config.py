"""
Configurazione dell'applicazione VCriptoV.

Nessun file .env da modificare a mano: tutte le chiavi/segreti necessari al
funzionamento del backend (chiave di sessione Flask, chiave di firma delle
licenze, chiave di cifratura delle credenziali exchange) vengono generate
automaticamente al primo avvio e salvate nella cartella `instance/`.

Le impostazioni dell'UTENTE (email, API key/secret dell'exchange, token
Telegram) NON stanno qui: si inseriscono dalla pagina web "Impostazioni".
"""

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


def load_or_create_secret(name: str, nbytes: int = 32) -> bytes:
    """Ritorna un segreto persistente, generandolo la prima volta."""
    path = INSTANCE_DIR / name
    if path.exists():
        return path.read_bytes()
    value = secrets.token_bytes(nbytes)
    path.write_bytes(value)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # su alcuni filesystem (Windows) chmod è un no-op
    return value


def load_stripe_key() -> str | None:
    """Restituisce la Stripe Secret Key da usare per i pagamenti.

    Ordine di ricerca (la prima che trova vince):
      1. variabile d'ambiente STRIPE_SECRET_KEY (comoda in produzione/hosting);
      2. file locale `instance/stripe.key` — incolla qui dentro la tua chiave,
         UNA VOLTA, e funziona per sempre. Questo file è ignorato da git
         (vedi .gitignore) quindi NON finisce mai nel repository/GitHub.

    In questo modo la chiave sta "hardcoded" in un unico posto fisso, senza
    dover impostare variabili d'ambiente ad ogni avvio, ma resta fuori dal
    codice sorgente versionato.
    """
    env_key = os.environ.get("STRIPE_SECRET_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    key_file = INSTANCE_DIR / "stripe.key"
    if key_file.exists():
        content = key_file.read_text(encoding="utf-8").strip()
        if content:
            return content

    return None


class Config:
    SECRET_KEY = load_or_create_secret("flask_secret.key")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{(INSTANCE_DIR / 'vcriptov.db').as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Chiave usata per firmare (HMAC) i codici licenza.
    LICENSE_SIGNING_KEY = load_or_create_secret("license_signing.key")

    # Ogni quanti secondi gira il motore di trading in background.
    BOT_INTERVAL_SECONDS = int(os.environ.get("BOT_INTERVAL_SECONDS", "30"))

    # Capitale virtuale (paper trading) assegnato a ogni licenza attiva.
    STARTING_EQUITY = float(os.environ.get("STARTING_EQUITY", "10000"))
