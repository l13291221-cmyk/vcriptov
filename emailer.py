"""
Invio email (best-effort) — es. la ricevuta col codice di attivazione.

Si configura con variabili d'ambiente (niente credenziali nel codice):
  SMTP_HOST      es. smtp.gmail.com
  SMTP_PORT      es. 587
  SMTP_USER      es. assistenza.vcriptov@gmail.com
  SMTP_PASSWORD  la "password per app" di Gmail (NON la password normale)
  SMTP_FROM      (facoltativo) mittente mostrato; default = SMTP_USER

Se non è configurato, l'invio viene semplicemente saltato senza errori.
Per Gmail: attiva la verifica in due passaggi e crea una "App password".
"""

import os
import smtplib
import ssl
from email.message import EmailMessage


def email_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER")
                and os.environ.get("SMTP_PASSWORD"))


def send_email(to: str, subject: str, body: str, attachment: str | None = None) -> bool:
    """Invia un'email. Se `attachment` è il percorso di un file esistente, lo
    allega (usato per il backup del database inviato via email)."""
    if not to or not email_configured():
        return False
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ.get("SMTP_FROM", user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(body)

    if attachment and os.path.exists(attachment):
        try:
            with open(attachment, "rb") as fh:
                data = fh.read()
            msg.add_attachment(data, maintype="application", subtype="octet-stream",
                               filename=os.path.basename(attachment))
        except OSError:
            pass

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context()) as s:
                s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(user, password)
                s.send_message(msg)
        return True
    except Exception:
        return False


def send_activation_email(to: str, plan_name: str, code: str) -> bool:
    body = (
        f"Grazie per aver scelto VCriptoV!\n\n"
        f"Piano: {plan_name}\n"
        f"Il tuo codice di attivazione:\n\n    {code}\n\n"
        f"Inseriscilo nel sito (Hai già un codice? Attiva qui) per accedere alla dashboard.\n\n"
        f"⚠️ I segnali del bot sono analisi automatiche, non accurate al 100% e non\n"
        f"costituiscono consulenza finanziaria. Investendo rischi il tuo capitale.\n\n"
        f"Assistenza: assistenza.vcriptov@gmail.com\n"
        f"— VCriptoV"
    )
    return send_email(to, "VCriptoV — Il tuo codice di attivazione", body)
