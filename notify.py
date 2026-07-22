"""
Notifiche Telegram (best-effort) + messaggi interattivi con bottoni.

- send_telegram:        messaggio semplice.
- send_signal_message:  messaggio con i tasti "✅ Investi" / "❌ Non investire".
- get_updates:          riceve i tap dei bottoni (long polling, niente webhook).
- answer_callback:      conferma il tap (toglie il "caricamento" sul bottone).
- edit_message:         aggiorna il testo del messaggio dopo l'azione.

Ogni errore di rete viene gestito senza bloccare il resto.
"""

import requests

_API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, payload: dict, timeout: int = 10):
    if not token:
        return None
    try:
        resp = requests.post(_API.format(token=token, method=method), json=payload, timeout=timeout)
        data = resp.json()
        return data if data.get("ok") else None
    except (requests.RequestException, ValueError):
        return None


def send_telegram(token: str, chat_id: str, text: str) -> bool:
    if not token or not chat_id:
        return False
    return _call(token, "sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}) is not None


def send_signal_message(token: str, chat_id: str, text: str, signal_id: int):
    """Invia il segnale con i due bottoni. Ritorna il message_id (o None)."""
    if not token or not chat_id:
        return None
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Investi", "callback_data": f"invest:{signal_id}"},
            {"text": "❌ Non investire", "callback_data": f"skip:{signal_id}"},
        ]]
    }
    data = _call(token, "sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
    })
    if data:
        return str(data["result"]["message_id"])
    return None


def get_updates(token: str, offset: int | None = None, timeout: int = 0):
    """Ritorna la lista di update (inclusi i tap dei bottoni)."""
    if not token:
        return []
    payload = {"timeout": timeout, "allowed_updates": ["callback_query"]}
    if offset is not None:
        payload["offset"] = offset
    data = _call(token, "getUpdates", payload, timeout=timeout + 10)
    return data["result"] if data else []


def answer_callback(token: str, callback_query_id: str, text: str = ""):
    _call(token, "answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text})


def edit_message(token: str, chat_id: str, message_id: str, text: str):
    _call(token, "editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    })
