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

from analysis import answer_question
from config import Config
from emailer import send_email
from exchange_account import place_signal_order
from market import market
from models import License, PriceAlert, Setting, Signal, db
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
            self._update_signal_outcomes(lic, prices)
            self._monitor_open_investments(lic, prices)
            self._check_price_alerts(lic, prices)
            self._maybe_expiry_reminder(lic)
            self._maybe_weekly_summary(lic)
            self._maybe_monthly_report(lic)

        db.session.commit()
        self.last_tick = datetime.utcnow()
        self.tick_count += 1
        self._maybe_backup()

    def _maybe_monthly_report(self, lic):
        """Una volta al mese manda per email il resoconto personale: quanto ha
        reso il bot con i segnali (guadagno stimato) e quante perdite ha evitato
        il guardiano avvisando in tempo."""
        if not lic.email or lic.email.endswith("@vcriptov.local"):
            return
        now = datetime.utcnow()
        this_month = now.strftime("%Y-%m")
        if lic.last_report_month is None:
            lic.last_report_month = this_month  # primo giro: parte dal mese dopo
            return
        if lic.last_report_month == this_month:
            return

        month_ago = now - timedelta(days=31)
        sigs = Signal.query.filter(
            Signal.license_id == lic.id, Signal.created_at >= month_ago,
            Signal.outcome.isnot(None),
        ).all()
        gain = 0.0
        saved = 0.0
        wins = losses = 0
        for s in sigs:
            base = s.max_order_eur or 20.0
            if s.outcome == "win":
                gain += base * (s.take_profit_pct or 0) / 100.0
                wins += 1
            else:
                loss = base * (s.stop_loss_pct or 0) / 100.0
                gain -= loss
                losses += 1
                # "Risparmio": se il guardiano aveva avvisato di uscire, conta la
                # perdita che l'utente poteva evitare dando retta all'avviso.
                if s.warn_loss_sent:
                    saved += loss

        lic.last_report_month = this_month
        if not sigs:
            return  # niente attività questo mese: niente email inutile

        wr = round(wins / len(sigs) * 100) if sigs else 0
        body = (
            f"Ciao,\n\nEcco il tuo resoconto mensile VCriptoV.\n\n"
            f"Segnali chiusi nel mese: {len(sigs)}\n"
            f"A target: {wins}   In perdita: {losses}   (successo {wr}%)\n"
            f"Guadagno stimato dai segnali: {gain:+.2f}€\n"
            f"Perdite che potevi evitare dando retta agli avvisi del guardiano: ~{saved:.2f}€\n\n"
            f"Ricorda: sono stime basate sui segnali, non profitti garantiti. "
            f"Decidi sempre tu ogni investimento.\n\n"
            f"— Il team VCriptoV"
        )
        send_email(lic.email, "VCriptoV — Il tuo resoconto mensile", body)

    def _maybe_backup(self):
        """Backup automatico del database SQLite, una volta al giorno, tenendo
        gli ultimi 7 file. Su database esterni (Postgres) non fa nulla."""
        import os
        import shutil
        from config import INSTANCE_DIR

        db_file = INSTANCE_DIR / "vcriptov.db"
        if not db_file.exists():
            return  # DB esterno (Postgres) o non ancora creato
        now = datetime.utcnow()
        last = getattr(self, "_last_backup_day", None)
        if last == now.date():
            return
        self._last_backup_day = now.date()
        backup_dir = INSTANCE_DIR / "backups"
        try:
            backup_dir.mkdir(exist_ok=True)
            dest = backup_dir / f"vcriptov-{now:%Y%m%d}.db"
            shutil.copy2(db_file, dest)
            # Tieni solo gli ultimi 7 backup.
            files = sorted(backup_dir.glob("vcriptov-*.db"))
            for old in files[:-7]:
                try:
                    os.remove(old)
                except OSError:
                    pass
        except Exception as exc:
            self.app.logger.warning("Backup DB non riuscito: %s", exc)

    def _update_signal_outcomes(self, lic, prices):
        """Track record: segna se un segnale ha raggiunto il take profit (win) o
        lo stop loss (loss). Se la posizione era stata investita davvero
        ('executed'), manda anche il RIEPILOGO del guardiano su Telegram con il
        risultato finale (+X% / −Y%)."""
        open_sigs = Signal.query.filter(
            Signal.license_id == lic.id, Signal.outcome.is_(None)
        ).all()
        for sig in open_sigs:
            price = prices.get(sig.symbol)
            if not price:
                continue
            tp = sig.ref_price * (1 + (sig.take_profit_pct or 0) / 100)
            sl = sig.ref_price * (1 - (sig.stop_loss_pct or 0) / 100)
            if price >= tp:
                sig.outcome = "win"
            elif price <= sl:
                sig.outcome = "loss"
            else:
                continue
            # Riepilogo di chiusura, solo per gli investimenti reali.
            if sig.status == "executed":
                self._send_close_summary(lic, sig, price)

    def _send_close_summary(self, lic, sig, price):
        settings = lic.settings
        if not (settings and self._telegram_ready(lic, settings)):
            return
        change = (price / sig.ref_price - 1.0) * 100.0 if sig.ref_price else 0.0
        coin = sig.symbol.replace("/USDT", "")
        if sig.outcome == "win":
            head = f"✅ <b>Chiusa in guadagno su {coin}</b>"
        else:
            head = f"🔻 <b>Chiusa in perdita su {coin}</b>"
        send_telegram(
            decrypt(settings.telegram_token_enc), settings.telegram_chat_id,
            f"{head}\n"
            f"Risultato finale: <b>{change:+.1f}%</b>\n"
            f"(ingresso ~{sig.ref_price:,.4f} → uscita ~{price:,.4f})\n\n"
            f"⚠️ <i>Controlla la posizione anche sul tuo exchange. Non è "
            f"consulenza finanziaria.</i>",
        )

    def _monitor_open_investments(self, lic, prices):
        """GUARDIANO DELLA POSIZIONE. Dopo che l'utente tocca "Investi" e l'ordine
        parte (segnale 'executed'), il bot sorveglia quella posizione e avvisa su
        Telegram dicendo cosa fare:
          • se sta andando GIÙ forte (vicino allo stop, o in perdita con trend
            girato al ribasso) → suggerisce di CHIUDERE per limitare la perdita;
          • se è già MOLTO in guadagno (vicino all'obiettivo) → suggerisce di
            INCASSARE.
        Manda al massimo un avviso per tipo, per non intasare la chat."""
        settings = lic.settings
        if not (settings and self._telegram_ready(lic, settings)):
            return
        open_sigs = Signal.query.filter(
            Signal.license_id == lic.id,
            Signal.status == "executed",
            Signal.outcome.is_(None),
        ).all()
        if not open_sigs:
            return
        token = decrypt(settings.telegram_token_enc)
        chat = settings.telegram_chat_id
        fast = settings.fast_ma or 5
        slow = settings.slow_ma or 20
        for sig in open_sigs:
            price = prices.get(sig.symbol)
            if not price or not sig.ref_price:
                continue
            change = (price / sig.ref_price - 1.0) * 100.0
            sl = sig.stop_loss_pct or 8.0
            tp = sig.take_profit_pct or 15.0
            coin = sig.symbol.replace("/USDT", "")
            f = market.sma(sig.symbol, fast)
            s = market.sma(sig.symbol, slow)
            trend_down = (f is not None and s is not None and f < s)

            # Perdita seria: vicino allo stop, oppure già in rosso con trend debole.
            if not sig.warn_loss_sent and (change <= -sl * 0.6 or (change <= -sl * 0.35 and trend_down)):
                send_telegram(
                    token, chat,
                    f"🔻 <b>Attenzione su {coin}</b>\n"
                    f"La posizione che hai aperto è a <b>{change:+.1f}%</b> "
                    f"(stop loss a −{sl:.0f}%).\n"
                    f"Il bot vede che <b>sta scendendo</b> e l'andamento è debole: "
                    f"forse non vale la pena aspettare.\n"
                    f"👉 Valuta di <b>chiudere ora per limitare la perdita</b>.\n\n"
                    f"⚠️ <i>Non è consulenza finanziaria: decidi sempre tu.</i>",
                )
                sig.warn_loss_sent = True

            # Molto in guadagno: vicino all'obiettivo → valuta di incassare.
            elif not sig.warn_profit_sent and change >= tp * 0.75:
                send_telegram(
                    token, chat,
                    f"🚀 <b>Bene su {coin}!</b>\n"
                    f"La tua posizione è a <b>{change:+.1f}%</b> (obiettivo +{tp:.0f}%).\n"
                    f"Sei <b>molto in guadagno</b>: potrebbe essere il momento di "
                    f"<b>incassare</b> una parte o tutto, prima che il prezzo torni indietro.\n\n"
                    f"⚠️ <i>Non è consulenza finanziaria: decidi sempre tu.</i>",
                )
                sig.warn_profit_sent = True

    def _check_price_alerts(self, lic, prices):
        settings = lic.settings
        if not (settings and self._telegram_ready(lic, settings)):
            return
        for a in PriceAlert.query.filter_by(license_id=lic.id, active=True).all():
            price = prices.get(a.symbol)
            if not price:
                continue
            hit = (a.direction == "below" and price <= a.target) or \
                  (a.direction == "above" and price >= a.target)
            if hit:
                coin = a.symbol.replace("/USDT", "")
                verso = "sceso sotto" if a.direction == "below" else "salito sopra"
                send_telegram(
                    decrypt(settings.telegram_token_enc), settings.telegram_chat_id,
                    f"🔔 <b>Avviso prezzo</b>\n{coin} è {verso} {a.target:g}$. "
                    f"Prezzo attuale: {price:,.4f}$",
                )
                a.active = False

    def _maybe_weekly_summary(self, lic):
        settings = lic.settings
        if not (settings and self._telegram_ready(lic, settings)):
            return
        now = datetime.utcnow()
        if lic.last_summary_at is None:
            lic.last_summary_at = now  # primo giro: parte dalla settimana successiva
            return
        if now - lic.last_summary_at < timedelta(days=7):
            return
        week_ago = now - timedelta(days=7)
        sigs = Signal.query.filter(
            Signal.license_id == lic.id, Signal.created_at >= week_ago
        ).all()
        wins = sum(1 for s in sigs if s.outcome == "win")
        losses = sum(1 for s in sigs if s.outcome == "loss")
        send_telegram(
            decrypt(settings.telegram_token_enc), settings.telegram_chat_id,
            f"📅 <b>Riepilogo settimanale VCriptoV</b>\n"
            f"Segnali inviati: <b>{len(sigs)}</b>\n"
            f"🎯 A target: {wins}   🔻 In perdita: {losses}\n\n"
            f"⚠️ <i>Nessun bot è accurato al 100%. Valuta sempre tu.</i>",
        )
        lic.last_summary_at = now

    def _maybe_expiry_reminder(self, lic):
        """Manda una volta il promemoria quando mancano <= 3 giorni alla scadenza."""
        if lic.expires_at is None or lic.expiry_reminder_sent:
            return
        delta = lic.expires_at - datetime.utcnow()
        if not (timedelta(0) < delta <= timedelta(days=3)):
            return
        msg = (
            f"⏳ Il tuo abbonamento VCriptoV scade il {lic.expires_at:%d/%m/%Y}. "
            f"Rinnova per non perdere l'accesso ai segnali."
        )
        settings = lic.settings
        if settings and self._telegram_ready(lic, settings):
            send_telegram(decrypt(settings.telegram_token_enc), settings.telegram_chat_id,
                          f"<b>VCriptoV</b>\n{msg}")
        if lic.email and not lic.email.endswith("@vcriptov.local"):
            send_email(lic.email, "VCriptoV — Abbonamento in scadenza", msg)
        lic.expiry_reminder_sent = True

    def _process_license(self, lic: License, prices: dict[str, float]):
        """Manda automaticamente i segnali interattivi su Telegram (senza che
        l'utente scriva). Bastano Telegram collegato: se il TRADING REALE è
        acceso, toccando "Investi" l'ordine parte davvero su Kraken; altrimenti
        il segnale è solo informativo. Nessun paper trading, nessun dato finto."""
        settings = lic.settings
        if not (settings and self._telegram_ready(lic, settings)):
            return

        # FOCUS: se l'utente ha un investimento aperto (ha toccato "Investi" e
        # l'ordine è partito), il bot si concentra SOLO su quello — niente nuovi
        # segnali su altre cripto finché quella posizione non si chiude.
        open_invest = (
            Signal.query.filter_by(license_id=lic.id, status="executed")
            .filter(Signal.outcome.is_(None))
            .first()
        )
        if open_invest:
            return

        fast = settings.fast_ma or 5
        slow = settings.slow_ma or 20
        # Solo le crypto scelte dall'utente (vuoto = tutte quelle del piano).
        symbols = plan_symbols(lic.plan)
        if settings.signal_symbols:
            chosen = set(settings.signal_symbols.split(","))
            symbols = [s for s in symbols if s in chosen]
        for symbol in symbols:
            if prices.get(symbol):
                self._maybe_send_signal(lic, settings, symbol, prices[symbol], fast, slow)

    # ---- filtro qualità mercato (meno segnali, ma migliori) ------------
    def _recent_volatility(self, symbol) -> float | None:
        """Ampiezza percentuale del prezzo negli ultimi minuti. Serve a scartare
        i mercati fermi (piatti) e quelli troppo nervosi."""
        h = market.history(symbol)
        if len(h) < 6:
            return None
        window = h[-12:]
        mean = sum(window) / len(window)
        if mean <= 0:
            return None
        return (max(window) - min(window)) / mean * 100.0

    def _market_is_good(self, symbol) -> bool:
        vol = self._recent_volatility(symbol)
        if vol is None:
            return True  # storia insufficiente: non blocco
        # Mercato PIATTO (fermo) o troppo NERVOSO → niente segnale.
        return 0.5 <= vol <= 10.0

    def _is_quiet_hours(self) -> bool:
        """Ore notturne a bassa liquidità in ITALIA (01:00–06:00), quando i
        movimenti sono spesso falsi: meglio non mandare segnali. Usa il vero fuso
        orario italiano, con l'ora legale che cambia da sola. Se il sistema non
        ha i dati dei fusi, ripiega su un'approssimazione (UTC+1)."""
        try:
            from zoneinfo import ZoneInfo
            hour = datetime.now(ZoneInfo("Europe/Rome")).hour
        except Exception:
            hour = (datetime.utcnow().hour + 1) % 24  # CET approssimato
        return 1 <= hour < 6

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

        # Meno segnali ma migliori: salta i mercati fermi o troppo nervosi e le
        # ore notturne a bassa liquidità.
        if self._is_quiet_hours() or not self._market_is_good(symbol):
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
            f"Vuoi investire? Tocca un bottone qui sotto.\n\n"
            f"⚠️ <i>Analisi automatica, non accurata al 100%. Non è consulenza "
            f"finanziaria: verifica sempre di persona prima di investire e non "
            f"affidarti ciecamente al bot. Rischi il tuo capitale.</i>"
        )
        token = decrypt(settings.telegram_token_enc)
        msg_id = send_signal_message(token, settings.telegram_chat_id, text, sig.id)
        if msg_id:
            sig.telegram_message_id = msg_id
        else:
            sig.status = "failed"
            sig.result = "Invio del messaggio Telegram non riuscito."

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
        """Thread separato: risponde ai messaggi e ai tap 'Investi/Non investire'."""
        while not self._stop.is_set():
            try:
                with self.app.app_context():
                    self._poll_telegram()
            except Exception as exc:  # non far morire il thread
                self.app.logger.exception("Errore nel listener Telegram: %s", exc)
            self._stop.wait(3)

    def _poll_telegram(self):
        # Un bot Telegram per cliente: interrogo ogni token configurato.
        settings_list = Setting.query.filter(Setting.telegram_token_enc.isnot(None)).all()
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
                    continue
                msg = update.get("message")
                if msg and msg.get("text"):
                    self._handle_message(token, s, msg)

    def _handle_message(self, token, settings, msg):
        """Risponde a una domanda scritta su Telegram (es. 'analizza il mercato')."""
        chat_id = str((msg.get("chat") or {}).get("id", ""))
        # Rispondo solo al proprietario configurato (il suo chat_id).
        if settings.telegram_chat_id and chat_id and chat_id != str(settings.telegram_chat_id):
            return
        reply = answer_question(msg.get("text", ""))
        send_telegram(token, chat_id or settings.telegram_chat_id, reply)

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
                answer_callback(token, cq_id, "Attiva il Trading reale e collega Kraken per investire davvero")
                if msg_id:
                    edit_message(token, chat_id, msg_id,
                                 "ℹ️ Per investire davvero attiva il <b>Trading reale</b> e collega "
                                 "il tuo Kraken nelle Impostazioni del sito. (Segnale solo informativo.)")
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
                        f"🛑 SL {result.get('stop_loss')}  🎯 TP {result.get('take_profit')}\n\n"
                        f"⚠️ <i>Ricorda: nessun bot è accurato al 100%. Controlla "
                        f"tu la posizione sul tuo exchange.</i>",
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
