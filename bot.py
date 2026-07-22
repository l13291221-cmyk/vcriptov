"""
Motore di trading in background (paper trading / simulazione).

Ogni `interval` secondi (default 30):
  1. avanza il feed dei prezzi;
  2. per ogni licenza attiva applica una strategia a incrocio di medie mobili
     sui simboli consentiti dal piano, aprendo/chiudendo posizioni virtuali;
  3. aggiorna il portafoglio (cash + valore posizioni) e salva un punto della
     curva di equity;
  4. invia notifiche Telegram se configurate (piani Pro/VIP/Lifetime).

ATTENZIONE: è una SIMULAZIONE didattica. Non esegue ordini reali sull'exchange
e non costituisce consulenza finanziaria.
"""

import threading
import time
from datetime import datetime

from config import Config
from market import market
from models import EquityPoint, License, Portfolio, Setting, Trade, db
from notify import send_telegram
from plans import get_plan, plan_symbols
from security import decrypt


class TradingEngine:
    def __init__(self, app):
        self.app = app
        self.interval = Config.BOT_INTERVAL_SECONDS
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.last_tick: datetime | None = None
        self.tick_count = 0

    # ---- ciclo di vita -------------------------------------------------
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="trading-engine", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        # Primo tick quasi subito, poi a intervalli regolari.
        while not self._stop.is_set():
            try:
                with self.app.app_context():
                    self.tick()
            except Exception as exc:  # non far morire mai il thread
                self.app.logger.exception("Errore nel tick del motore: %s", exc)
            self._stop.wait(self.interval)

    # ---- logica di trading --------------------------------------------
    def tick(self):
        market.step()
        prices = market.all_prices()

        licenses = License.query.filter_by(active=True, activated=True).all()
        for lic in licenses:
            self._process_license(lic, prices)

        db.session.commit()
        self.last_tick = datetime.utcnow()
        self.tick_count += 1

    def _process_license(self, lic: License, prices: dict[str, float]):
        settings = lic.settings
        portfolio = lic.portfolio
        if portfolio is None:
            portfolio = Portfolio(
                license_id=lic.id,
                cash=Config.STARTING_EQUITY,
                starting_equity=Config.STARTING_EQUITY,
            )
            db.session.add(portfolio)
            db.session.flush()

        if settings and not settings.trading_enabled:
            self._record_equity(lic, portfolio, prices)
            return

        fast = settings.fast_ma if settings else 5
        slow = settings.slow_ma if settings else 20
        risk = settings.risk_per_trade if settings else 2.0

        symbols = plan_symbols(lic.plan)
        open_trades = {
            t.symbol: t
            for t in Trade.query.filter_by(license_id=lic.id, status="open").all()
        }

        for symbol in symbols:
            price = prices.get(symbol)
            if not price:
                continue
            sma_fast = market.sma(symbol, fast)
            sma_slow = market.sma(symbol, slow)
            if sma_fast is None or sma_slow is None:
                continue

            has_position = symbol in open_trades

            # Segnale long: media veloce sopra la lenta (momentum rialzista).
            if sma_fast > sma_slow and not has_position:
                self._open_trade(lic, portfolio, settings, symbol, price, risk)
            # Uscita: media veloce scende sotto la lenta.
            elif sma_fast < sma_slow and has_position:
                self._close_trade(lic, portfolio, settings, open_trades[symbol], price)

        self._record_equity(lic, portfolio, prices)

    def _open_trade(self, lic, portfolio, settings, symbol, price, risk_pct):
        equity = self._equity_value(portfolio)
        alloc = equity * (max(0.1, min(risk_pct, 20)) / 100.0) * 5  # posizione ~5x il rischio
        alloc = min(alloc, portfolio.cash)
        if alloc < 10:  # non aprire posizioni microscopiche
            return
        qty = alloc / price
        portfolio.cash -= alloc
        trade = Trade(
            license_id=lic.id,
            symbol=symbol,
            side="long",
            qty=qty,
            entry_price=price,
            status="open",
            opened_at=datetime.utcnow(),
        )
        db.session.add(trade)
        self._notify(settings, f"🟢 APERTURA {symbol} @ {price:,.4f} (qty {qty:.4f})")

    def _close_trade(self, lic, portfolio, settings, trade, price):
        proceeds = trade.qty * price
        trade.exit_price = price
        trade.pnl = (price - trade.entry_price) * trade.qty
        trade.status = "closed"
        trade.closed_at = datetime.utcnow()
        portfolio.cash += proceeds
        emoji = "✅" if trade.pnl >= 0 else "🔻"
        self._notify(
            settings,
            f"{emoji} CHIUSURA {trade.symbol} @ {price:,.4f} | P&L {trade.pnl:+,.2f} USDT",
        )

    def _equity_value(self, portfolio) -> float:
        """Equity = cash + valore di mercato delle posizioni aperte."""
        prices = market.all_prices()
        open_trades = Trade.query.filter_by(
            license_id=portfolio.license_id, status="open"
        ).all()
        positions_value = sum(t.qty * prices.get(t.symbol, t.entry_price) for t in open_trades)
        return portfolio.cash + positions_value

    def _record_equity(self, lic, portfolio, prices):
        open_trades = Trade.query.filter_by(license_id=lic.id, status="open").all()
        positions_value = sum(t.qty * prices.get(t.symbol, t.entry_price) for t in open_trades)
        equity = portfolio.cash + positions_value
        db.session.add(EquityPoint(license_id=lic.id, equity=equity, ts=datetime.utcnow()))

        # Mantieni la curva a max ~500 punti per licenza.
        count = EquityPoint.query.filter_by(license_id=lic.id).count()
        if count > 500:
            oldest = (
                EquityPoint.query.filter_by(license_id=lic.id)
                .order_by(EquityPoint.ts.asc())
                .limit(count - 500)
                .all()
            )
            for p in oldest:
                db.session.delete(p)

    def _notify(self, settings, text):
        if not settings:
            return
        plan = None
        try:
            plan = get_plan(settings.license.plan)
        except Exception:
            plan = None
        if not plan or not plan.get("telegram"):
            return
        token = decrypt(settings.telegram_token_enc)
        if token and settings.telegram_chat_id:
            send_telegram(token, settings.telegram_chat_id, f"<b>VCriptoV</b>\n{text}")


engine: TradingEngine | None = None


def init_engine(app) -> TradingEngine:
    global engine
    if engine is None:
        engine = TradingEngine(app)
    return engine
