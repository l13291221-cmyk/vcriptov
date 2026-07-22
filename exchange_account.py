"""
Collegamento REALE al conto exchange del singolo cliente (Kraken di default),
tramite ccxt e le sue chiavi API personali (cifrate nel DB).

Serve per DUE cose:
  1. leggere il conto vero (saldo + operazioni) da mostrare in dashboard;
  2. piazzare ordini VERI con stop-loss e take-profit quando il cliente tocca
     "Investi" sul messaggio Telegram.

⚠️ CODICE CHE MUOVE SOLDI VERI. Non è testabile in questo ambiente (niente rete
verso l'exchange, nessun conto reale). Testalo TU sul tuo conto con importi
minimi prima di usarlo con i clienti. I dettagli di stop-loss/take-profit e i
nomi dei simboli possono richiedere piccoli aggiustamenti a seconda
dell'exchange.
"""

import logging

try:
    import ccxt
except ImportError:
    ccxt = None

from security import decrypt

log = logging.getLogger(__name__)


def build_exchange(setting):
    """Crea un'istanza ccxt autenticata con le chiavi del cliente, o None."""
    if ccxt is None or setting is None:
        return None
    api_key = decrypt(setting.api_key_enc)
    api_secret = decrypt(setting.api_secret_enc)
    if not api_key or not api_secret:
        return None
    exchange_id = (setting.exchange or "kraken").lower()
    if not hasattr(ccxt, exchange_id):
        return None
    try:
        klass = getattr(ccxt, exchange_id)
        return klass({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
    except Exception as exc:  # pragma: no cover
        log.warning("Impossibile creare l'exchange del cliente: %s", exc)
        return None


def account_snapshot(setting) -> dict:
    """Legge saldo e ultime operazioni REALI dal conto del cliente (sola lettura)."""
    ex = build_exchange(setting)
    if ex is None:
        return {"connected": False, "error": "Conto non collegato (chiavi mancanti)."}
    try:
        balance = ex.fetch_balance()
        totals = {a: v for a, v in balance.get("total", {}).items() if v and v > 0}
    except Exception as exc:
        return {"connected": False, "error": f"Errore lettura saldo: {exc}"}

    trades = []
    try:
        raw = ex.fetch_my_trades(limit=50)
        for t in raw[-50:]:
            trades.append({
                "symbol": t.get("symbol"),
                "side": t.get("side"),
                "amount": t.get("amount"),
                "price": t.get("price"),
                "cost": t.get("cost"),
                "fee": (t.get("fee") or {}).get("cost"),
                "time": t.get("datetime"),
            })
    except Exception as exc:
        # Il saldo c'è ma lo storico no: non è un errore bloccante.
        log.info("Storico operazioni non disponibile: %s", exc)

    return {"connected": True, "balances": totals, "trades": list(reversed(trades))}


def place_signal_order(setting, symbol: str, side: str, max_order_eur: float,
                       stop_loss_pct: float, take_profit_pct: float) -> dict:
    """Piazza un ordine REALE a mercato + protezioni stop-loss/take-profit.

    Ritorna {ok: bool, ...}. NON solleva eccezioni: le racchiude nel risultato.
    """
    ex = build_exchange(setting)
    if ex is None:
        return {"ok": False, "error": "Conto Kraken non collegato o chiavi non valide."}

    try:
        ticker = ex.fetch_ticker(symbol)
        price = float(ticker.get("last") or ticker.get("close"))
        if not price:
            return {"ok": False, "error": "Prezzo non disponibile per " + symbol}

        # Dimensione ordine limitata dal tetto massimo (in EUR ~ USDT).
        amount = max(max_order_eur, 1.0) / price
        amount = float(ex.amount_to_precision(symbol, amount))

        # 1) Ordine di ingresso a mercato.
        entry = ex.create_order(symbol, "market", side, amount)

        # 2) Protezioni: stop-loss e take-profit come ordini di chiusura opposti.
        close_side = "sell" if side == "buy" else "buy"
        sl_price = price * (1 - stop_loss_pct / 100) if side == "buy" else price * (1 + stop_loss_pct / 100)
        tp_price = price * (1 + take_profit_pct / 100) if side == "buy" else price * (1 - take_profit_pct / 100)
        sl_price = float(ex.price_to_precision(symbol, sl_price))
        tp_price = float(ex.price_to_precision(symbol, tp_price))

        protections = {}
        try:
            protections["stop_loss"] = ex.create_order(
                symbol, "stop-loss", close_side, amount, None, {"stopPrice": sl_price}
            )
        except Exception as exc:
            protections["stop_loss_error"] = str(exc)
        try:
            protections["take_profit"] = ex.create_order(
                symbol, "take-profit", close_side, amount, tp_price, {"stopPrice": tp_price}
            )
        except Exception as exc:
            protections["take_profit_error"] = str(exc)

        return {
            "ok": True,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "entry_price": price,
            "stop_loss": sl_price,
            "take_profit": tp_price,
            "order_id": entry.get("id"),
            "protections": protections,
        }
    except Exception as exc:
        return {"ok": False, "error": f"Ordine fallito: {exc}"}
