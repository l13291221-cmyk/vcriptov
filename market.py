"""
Feed dei prezzi di mercato.

Per rendere l'applicazione autonoma e sempre funzionante (senza dipendere da
API esterne che potrebbero essere bloccate o a pagamento), i prezzi sono
simulati con un random walk realistico a partire da valori iniziali plausibili.

In produzione questa classe è il punto in cui collegheresti il feed reale
dell'exchange (es. Kraken/Binance ticker) usando le API dell'utente.
"""

import random
import threading
import time
from collections import defaultdict, deque

from plans import ALL_SYMBOLS, SEED_PRICES

_HISTORY_LEN = 200


class MarketData:
    def __init__(self):
        self._lock = threading.Lock()
        self._prices: dict[str, float] = dict(SEED_PRICES)
        self._history: dict[str, deque] = {
            s: deque([SEED_PRICES[s]], maxlen=_HISTORY_LEN) for s in ALL_SYMBOLS
        }
        # Leggera deriva per simbolo, così i grafici non sono tutti uguali.
        self._drift = {s: random.uniform(-0.0004, 0.0006) for s in ALL_SYMBOLS}

    def step(self):
        """Avanza di un tick tutti i prezzi (random walk geometrico)."""
        with self._lock:
            for s in ALL_SYMBOLS:
                price = self._prices[s]
                shock = random.gauss(0, 0.012)          # volatilità ~1.2%
                price *= (1 + self._drift[s] + shock)
                price = max(price, 0.0001)
                self._prices[s] = price
                self._history[s].append(price)

    def price(self, symbol: str) -> float:
        with self._lock:
            return self._prices.get(symbol, 0.0)

    def all_prices(self) -> dict[str, float]:
        with self._lock:
            return dict(self._prices)

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
