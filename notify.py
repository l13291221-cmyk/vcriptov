"""
Notifiche Telegram (best-effort).

Se il token del bot e il chat_id sono configurati nelle Impostazioni, invia un
messaggio. Ogni errore di rete viene ignorato silenziosamente per non bloccare
il motore di trading.
"""

import requests


def send_telegram(token: str, chat_id: str, text: str) -> bool:
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=8,
        )
        return resp.ok
    except requests.RequestException:
        return False
