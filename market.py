"""
Feed dei prezzi di mercato — DATI REALI.

Usa la libreria `ccxt` per leggere i prezzi veri da un exchange pubblico
(Kraken di default). Non servono le chiavi API per i prezzi di mercato: sono
dati pubblici. Le chiavi personali del cliente servono solo per operazioni sul
suo conto (saldo/ordini), non per la semplice analisi dei prezzi.

Robustezza: se la connessione all'exchange non è disponibile (es. offline, o
ambiente senza rete), l'app NON si rompe. In quel caso `source` diventa
"offline": i prezzi restano all'ultimo valore noto e il bot semplicemente non
genera nuovi segnali finché non torna la connessione. Nessun dato inventato.

Il campo `source` ("live" / "offline" / "starting") viene mostrato nella
dashboard così è sempre chiaro se i dati sono reali e aggiornati.
"""

import logging
import threading
import time
from collections import deque

from plans import ALL_SYMBOLS, SEED_PRICES

try:
    import ccxt
except ImportError:  # la libreria potrebbe non essere installata
    ccxt = None

log = logging.getLogger(__name__)

_HISTORY_LEN = 200

# Exchange da cui leggere i prezzi pubblici. I prezzi sono praticamente identici
# su tutti gli exchange, quindi ne basta uno come fonte dei dati di mercato.
MARKET_EXCHANGE = "kraken"


class MarketData:
    def __init__(self):
        self._lock = threading.Lock()
        self._prices: dict[str, float] = dict(SEED_PRICES)
        self._change: dict[str, float] = {}   # variazione % nelle 24h dal ticker
        self._history: dict[str, deque] = {s: deque(maxlen=_HISTORY_LEN) for s in ALL_SYMBOLS}
        self.source = "starting"          # "live" | "offline" | "starting"
        self.last_update: float | None = None
        self._exchange = None
        self._unsupported: set[str] = set()   # simboli non quotati su questo exchange
        self._bootstrapped = False
        self._init_exchange()

    # ------------------------------------------------------------------
    def _init_exchange(self):
        if ccxt is None:
            log.warning("ccxt non installato: impossibile leggere prezzi reali.")
            return
        try:
            self._exchange = getattr(ccxt, MARKET_EXCHANGE)({"enableRateLimit": True})
        except Exception as exc:  # pragma: no cover
            log.warning("Exchange %s non inizializzato: %s", MARKET_EXCHANGE, exc)
            self._exchange = None

    def _supported_symbols(self) -> list[str]:
        return [s for s in ALL_SYMBOLS if s not in self._unsupported]

    def _bootstrap(self):
        """Precarica lo storico recente (candele 1m) così le medie mobili sono
        subito calcolabili senza aspettare decine di tick."""
        if not self._exchange:
            return
        for sym in self._supported_symbols():
            try:
                ohlcv = self._exchange.fetch_ohlcv(sym, timeframe="1m", limit=60)
                closes = [float(c[4]) for c in ohlcv if c and c[4]]
                if closes:
                    with self._lock:
                        # Riempio lo storico per le medie mobili, ma NON tocco il
                        # prezzo attuale (già impostato, live, da _fetch_prices).
                        self._history[sym].clear()
                        for price in closes[-_HISTORY_LEN:]:
                            self._history[sym].append(price)
            except Exception:
                # Simbolo non disponibile su questo exchange: lo salto d'ora in poi.
                self._unsupported.add(sym)
        self._bootstrapped = True

    # ------------------------------------------------------------------
    def step(self):
        """Aggiorna i prezzi reali. PRIMA i prezzi (una chiamata veloce), così la
        dashboard si popola subito; POI, solo la prima volta, lo storico per le
        medie mobili (più lento)."""
        if self._exchange is None:
            self.source = "offline"
            return

        self._fetch_prices()

        # Il bootstrap dello storico avviene DOPO i prezzi, così non ritarda la
        # comparsa dei valori a schermo.
        if not self._bootstrapped:
            self._bootstrap()

    def _fetch_prices(self):
        symbols = self._supported_symbols()
        got: dict[str, float] = {}
        changes: dict[str, float] = {}

        def take(sym, t):
            last = t.get("last") or t.get("close")
            if last:
                got[sym] = float(last)
                pct = t.get("percentage")  # variazione % nelle 24h
                if pct is not None:
                    changes[sym] = float(pct)

        try:
            tickers = self._exchange.fetch_tickers(symbols)
            for sym, t in tickers.items():
                take(sym, t)
        except Exception:
            for sym in symbols:
                try:
                    take(sym, self._exchange.fetch_ticker(sym))
                except Exception:
                    self._unsupported.add(sym)

        if got:
            with self._lock:
                for sym, price in got.items():
                    self._prices[sym] = price
                    self._history[sym].append(price)
                self._change.update(changes)
                self.source = "live"
                self.last_update = time.time()
        else:
            self.source = "offline"

    # ------------------------------------------------------------------
    def price(self, symbol: str) -> float:
        with self._lock:
            return self._prices.get(symbol, 0.0)

    def all_prices(self) -> dict[str, float]:
        with self._lock:
            return dict(self._prices)

    def change(self, symbol: str) -> float | None:
        """Variazione percentuale nelle 24h (dal ticker dell'exchange)."""
        with self._lock:
            return self._change.get(symbol)

    def history(self, symbol: str) -> list[float]:
        with self._lock:
            return list(self._history.get(symbol, []))

    def sma(self, symbol: str, window: int) -> float | None:
        h = self.history(symbol)
        if len(h) < window:
            return None
        return sum(h[-window:]) / window


# Istanza condivisa a livello di processo.
market = MarketData()
