"""
Risponditore automatico alle domande su Telegram.

Non usa un modello di intelligenza artificiale esterno (che richiederebbe una
chiave a pagamento): risponde in linguaggio naturale usando i DATI DI MERCATO
REALI già raccolti dal bot (prezzi e medie mobili). Riconosce le domande più
comuni per parole chiave.

Esempi che capisce:
  - "analizza il mercato" / "come va il mercato" / "situazione"
  - "cosa c'è di meglio" / "cosa compro" / "opportunità" / "consigli"
  - "prezzo BTC" / "come sta ethereum"
  - "aiuto" / "comandi"
"""

from market import market
from plans import ALL_SYMBOLS

DISCLAIMER = (
    "\n\n⚠️ <i>Analisi automatica sui dati di mercato, non accurata al 100% e "
    "non è consulenza finanziaria. Controlla sempre di persona.</i>"
)


def _coin(sym: str) -> str:
    return sym.replace("/USDT", "")


def _fmt(price: float) -> str:
    if price >= 1:
        return f"{price:,.2f}"
    return f"{price:,.5f}"


def _stats():
    rows = []
    for s in ALL_SYMBOLS:
        price = market.price(s)
        if not price:
            continue
        fast = market.sma(s, 5)
        slow = market.sma(s, 20)
        hist = market.history(s)
        change = 0.0
        if len(hist) >= 2 and hist[-2]:
            change = (hist[-1] - hist[-2]) / hist[-2] * 100
        mom = None
        bull = False
        if fast and slow:
            mom = (fast - slow) / slow * 100
            bull = fast > slow
        rows.append({"coin": _coin(s), "price": price, "mom": mom, "change": change, "bull": bull})
    return rows


def _find_coin(text: str, rows):
    up = text.upper()
    names = {"BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL", "RIPPLE": "XRP",
             "CARDANO": "ADA", "DOGECOIN": "DOGE", "LITECOIN": "LTC"}
    for full, short in names.items():
        if full in up:
            return next((r for r in rows if r["coin"] == short), None)
    for r in rows:
        if r["coin"] in up:
            return r
    return None


def answer_question(text: str) -> str:
    t = (text or "").strip().lower()
    rows = _stats()
    have_data = any(r["mom"] is not None for r in rows)

    # Aiuto / saluti / avvio
    if any(k in t for k in ["aiuto", "help", "comandi", "/start", "start", "ciao", "salve"]):
        return (
            "👋 Ciao! Sono il tuo assistente di mercato. Puoi chiedermi:\n"
            "• <b>Analizza il mercato</b> — la situazione generale\n"
            "• <b>Cosa c'è di meglio</b> — le migliori opportunità ora\n"
            "• <b>Prezzo BTC</b> (o un'altra crypto) — prezzo e tendenza\n"
            "Riceverai comunque i segnali automatici con i tasti Investi." + DISCLAIMER
        )

    if not have_data:
        return (
            "📡 Sto ancora raccogliendo i dati di mercato (serve qualche minuto "
            "dopo l'avvio, e la connessione a internet). Riprova tra poco." + DISCLAIMER
        )

    # Domanda su una crypto specifica
    coin = _find_coin(t, rows)
    specific = coin and any(k in t for k in ["prezzo", "quanto", "come sta", "come va", "vale", coin["coin"].lower()])
    if coin and specific and not any(k in t for k in ["mercato", "meglio", "opportunit", "compr"]):
        trend = "📈 in salita" if coin["bull"] else "📉 in calo"
        return (
            f"<b>{coin['coin']}</b>\n"
            f"Prezzo: <b>${_fmt(coin['price'])}</b>\n"
            f"Tendenza: {trend}\n"
            f"Momentum: {coin['mom']:+.2f}%" + DISCLAIMER
        )

    # Migliori opportunità
    if any(k in t for k in ["meglio", "miglior", "compr", "opportunit", "consigl", "conviene", "investir"]):
        best = sorted([r for r in rows if r["bull"] and r["mom"] is not None],
                      key=lambda r: r["mom"], reverse=True)[:5]
        if not best:
            return ("🔎 Al momento nessuna crypto mostra un chiaro segnale di salita. "
                    "Meglio attendere un'occasione migliore." + DISCLAIMER)
        lines = "\n".join(
            f"{i+1}. <b>{r['coin']}</b> — ${_fmt(r['price'])}  (forza {r['mom']:+.2f}%)"
            for i, r in enumerate(best)
        )
        return "💡 <b>Migliori opportunità ora</b> (momentum rialzista):\n" + lines + DISCLAIMER

    # Analisi generale del mercato
    if any(k in t for k in ["mercato", "analizz", "analisi", "situazione", "come va", "generale", "oggi"]):
        bull = [r for r in rows if r["bull"]]
        gainers = sorted(rows, key=lambda r: r["change"], reverse=True)[:3]
        losers = sorted(rows, key=lambda r: r["change"])[:3]
        mood = "prevalentemente positivo 🟢" if len(bull) > len(rows) / 2 else "cauto / debole 🔴"
        g = ", ".join(f"{r['coin']} ({r['change']:+.2f}%)" for r in gainers)
        l = ", ".join(f"{r['coin']} ({r['change']:+.2f}%)" for r in losers)
        return (
            f"📊 <b>Analisi di mercato</b>\n"
            f"Umore generale: <b>{mood}</b>\n"
            f"Crypto in tendenza rialzista: <b>{len(bull)}</b> su {len(rows)}\n"
            f"🔼 Migliori ora: {g}\n"
            f"🔽 Peggiori ora: {l}" + DISCLAIMER
        )

    # Non ho capito
    return (
        "🤔 Non ho capito bene. Prova a scrivere:\n"
        "• <b>Analizza il mercato</b>\n"
        "• <b>Cosa c'è di meglio</b>\n"
        "• <b>Prezzo BTC</b>\n"
        "Oppure scrivi <b>aiuto</b>." + DISCLAIMER
    )
