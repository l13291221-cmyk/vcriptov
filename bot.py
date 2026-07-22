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
from datetime import datetime, timedelta

from config import Config
from exchange_account import place_signal_order
from market import market
from models import EquityPoint, License, Portfolio, Setting, Signal, Trade, db
from notify import answer_callback, edit_message, get_updates, send_signal_message, send_telegram
from plans import get_plan, plan_symbols
from security import decrypt


class TradingEngine:
    def __init__(self, app):
        self.app = app
        self.interval = Config.BOT_INTERVAL_SECONDS
        self._thread: threading.Thread | None = None
        self._tg_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.last_tick: datetime | None = None
        self.tick_count = 0
        self._tg_offsets: dict[str, int] = {}  # offset getUpdates per token

    # ---- ciclo di vita -------------------------------------------------
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="trading-engine", daemon=True)
        self._thread.start()
        # Secondo thread: ascolta i tap dei bottoni Telegram ed esegue gli ordini.
        self._tg_thread = threading.Thread(target=self._telegram_loop, name="telegram-listener", daemon=True)
        self._tg_thread.start()

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

        fast = settings.fast_ma if settings else 5
        slow = settings.slow_ma if settings else 20
        risk = settings.risk_per_trade if settings else 2.0

        # --- MODALITÀ TRADING REALE: manda segnali a bottoni su Telegram ---
        # (soldi veri: l'ordine parte solo quando il cliente tocca "Investi")
        if settings and settings.live_trading and self._telegram_ready(lic, settings):
            for symbol in plan_symbols(lic.plan):
                if prices.get(symbol):
                    self._maybe_send_signal(lic, settings, symbol, prices[symbol], fast, slow)
            self._record_equity(lic, portfolio, prices)
            return

        # --- MODALITÀ DEMO (paper trading, track record) ---
        if settings and not settings.trading_enabled:
            self._record_equity(lic, portfolio, prices)
            return

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

    # ---- modalità reale: generazione segnali interattivi ---------------
    def _telegram_ready(self, lic, settings) -> bool:
        plan = get_plan(lic.plan)
        return bool(plan and plan.get("telegram") and settings.telegram_chat_id
                    and decrypt(settings.telegram_token_enc))

    def _maybe_send_signal(self, lic, settings, symbol, price, fast, slow):
        sma_fast = market.sma(symbol, fast)
        sma_slow = market.sma(symbol, slow)
        if sma_fast is None or sma_slow is None:
            return
        if sma_fast <= sma_slow:   # segnale d'acquisto solo con momentum rialzista
            return

        # Anti-spam: niente nuovo segnale se ce n'è già uno recente per questo simbolo.
        recent = (
            Signal.query.filter_by(license_id=lic.id, symbol=symbol)
            .filter(Signal.created_at > datetime.utcnow() - timedelta(hours=6))
            .first()
        )
        if recent:
            return

        sl = settings.stop_loss_pct or 8.0
        tp = settings.take_profit_pct or 15.0
        cap = settings.max_order_eur or 20.0

        sig = Signal(
            license_id=lic.id, symbol=symbol, side="buy", ref_price=price,
            stop_loss_pct=sl, take_profit_pct=tp, max_order_eur=cap, status="pending",
        )
        db.session.add(sig)
        db.session.flush()  # per avere sig.id

        coin = symbol.replace("/USDT", "")
        text = (
            f"📈 <b>Segnale su {coin}</b>\n"
            f"Azione: <b>COMPRA</b> {coin}\n"
            f"Prezzo attuale: <b>{price:,.4f}</b>\n"
            f"🛑 Stop loss: <b>{sl:.1f}%</b>   🎯 Take profit: <b>{tp:.1f}%</b>\n"
            f"Importo: fino a <b>{cap:.0f}€</b>\n\n"
            f"Vuoi investire? Tocca un bottone qui sotto."
        )
        token = decrypt(settings.telegram_token_enc)
        msg_id = send_signal_message(token, settings.telegram_chat_id, text, sig.id)
        if msg_id:
            sig.telegram_message_id = msg_id
        else:
            sig.status = "failed"
            sig.result = "Invio del messaggio Telegram non riuscito."

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

    # ---- ascolto tap dei bottoni Telegram ed esecuzione ordini ---------
    def _telegram_loop(self):
        """Thread separato: raccoglie i tap 'Investi/Non investire' ed esegue."""
        while not self._stop.is_set():
            try:
                with self.app.app_context():
                    self._poll_telegram()
            except Exception as exc:  # non far morire il thread
                self.app.logger.exception("Errore nel listener Telegram: %s", exc)
            self._stop.wait(3)

    def _poll_telegram(self):
        # Un bot Telegram per cliente: interrogo il getUpdates di ogni token attivo.
        settings_list = (
            Setting.query.filter_by(live_trading=True)
            .filter(Setting.telegram_token_enc.isnot(None))
            .all()
        )
        seen_tokens = set()
        for s in settings_list:
            token = decrypt(s.telegram_token_enc)
            if not token or token in seen_tokens:
                continue
            seen_tokens.add(token)
            offset = self._tg_offsets.get(token)
            for update in get_updates(token, offset):
                self._tg_offsets[token] = update["update_id"] + 1
                cq = update.get("callback_query")
                if cq:
                    self._handle_callback(token, cq)

    def _handle_callback(self, token, cq):
        data = cq.get("data", "")
        cq_id = cq.get("id")
        try:
            action, sig_id = data.split(":", 1)
            sig = db.session.get(Signal, int(sig_id))
        except (ValueError, TypeError):
            answer_callback(token, cq_id, "Segnale non valido")
            return

        if not sig:
            answer_callback(token, cq_id, "Segnale scaduto")
            return

        lic = db.session.get(License, sig.license_id)
        settings = lic.settings if lic else None
        # Sicurezza: il tap deve arrivare dal bot del proprietario del segnale.
        if not settings or decrypt(settings.telegram_token_enc) != token:
            answer_callback(token, cq_id, "Non autorizzato")
            return

        chat_id = settings.telegram_chat_id
        msg_id = sig.telegram_message_id

        if sig.status != "pending":
            answer_callback(token, cq_id, "Segnale già gestito")
            return

        if action == "skip":
            sig.status = "declined"
            sig.resolved_at = datetime.utcnow()
            db.session.commit()
            answer_callback(token, cq_id, "Ok, nessun ordine")
            if msg_id:
                edit_message(token, chat_id, msg_id, "❌ Segnale ignorato. Nessun ordine effettuato.")
            return

        if action == "invest":
            if not settings.live_trading:
                answer_callback(token, cq_id, "Trading reale disattivato")
                return
            answer_callback(token, cq_id, "Eseguo l'ordine…")
            result = place_signal_order(
                settings, sig.symbol, sig.side, sig.max_order_eur,
                sig.stop_loss_pct, sig.take_profit_pct,
            )
            sig.resolved_at = datetime.utcnow()
            if result.get("ok"):
                sig.status = "executed"
                sig.result = f"OK id={result.get('order_id')} qty={result.get('amount')}"
                db.session.commit()
                if msg_id:
                    edit_message(
                        token, chat_id, msg_id,
                        f"✅ <b>Ordine eseguito</b> su {sig.symbol}\n"
                        f"Quantità: {result.get('amount')}\n"
                        f"Ingresso ~{result.get('entry_price')}\n"
                        f"🛑 SL {result.get('stop_loss')}  🎯 TP {result.get('take_profit')}",
                    )
            else:
                sig.status = "failed"
                sig.result = result.get("error", "errore")
                db.session.commit()
                if msg_id:
                    edit_message(token, chat_id, msg_id,
                                 f"⚠️ Ordine NON eseguito: {result.get('error')}")


engine: TradingEngine | None = None


def init_engine(app) -> TradingEngine:
    global engine
    if engine is None:
        engine = TradingEngine(app)
    return engine
