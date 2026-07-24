"""
Modelli del database (SQLAlchemy / SQLite).
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class License(db.Model):
    __tablename__ = "licenses"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    plan = db.Column(db.String(32), nullable=False)
    key = db.Column(db.String(64), nullable=False, unique=True, index=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    activated = db.Column(db.Boolean, default=False, nullable=False)
    banned = db.Column(db.Boolean, default=False, nullable=False)  # bannato dal creatore (sicurezza)
    paid = db.Column(db.Boolean, default=False)          # True se pagato con Stripe (non demo)
    influencer_slot = db.Column(db.Integer, nullable=True)  # 1..5, da quale influencer arriva
    # Nome dell'influencer FOTOGRAFATO al momento dell'iscrizione: non cambia
    # se in seguito rinomini lo slot, così l'attribuzione storica resta corretta.
    influencer_name = db.Column(db.String(120), nullable=True)
    terms_accepted = db.Column(db.Boolean, default=False)   # ha accettato rischi/termini
    device_id = db.Column(db.String(64), nullable=True)     # dispositivo a cui è legato il codice
    pending_device_id = db.Column(db.String(64), nullable=True)     # dispositivo in attesa di sblocco
    device_change_requested = db.Column(db.Boolean, default=False)  # ha chiesto accesso da nuovo device
    expires_at = db.Column(db.DateTime, nullable=True)              # scadenza abbonamento (None = mai)
    stripe_subscription_id = db.Column(db.String(120), nullable=True)  # id abbonamento Stripe (rinnovi)
    last_review_month = db.Column(db.String(7), nullable=True)      # "YYYY-MM" dell'ultima recensione
    recovery_phone = db.Column(db.String(40), nullable=True)        # telefono per recupero (influencer)
    expiry_reminder_sent = db.Column(db.Boolean, default=False)     # promemoria scadenza già inviato
    last_summary_at = db.Column(db.DateTime, nullable=True)         # ultimo riepilogo settimanale inviato
    last_report_month = db.Column(db.String(7), nullable=True)      # "YYYY-MM" dell'ultimo report email mensile
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activated_at = db.Column(db.DateTime, nullable=True)

    settings = db.relationship(
        "Setting", backref="license", uselist=False, cascade="all, delete-orphan"
    )
    portfolio = db.relationship(
        "Portfolio", backref="license", uselist=False, cascade="all, delete-orphan"
    )
    trades = db.relationship(
        "Trade", backref="license", cascade="all, delete-orphan"
    )
    equity_points = db.relationship(
        "EquityPoint", backref="license", cascade="all, delete-orphan"
    )


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), nullable=False)

    contact_email = db.Column(db.String(255), nullable=True)
    exchange = db.Column(db.String(64), default="kraken")

    # Credenziali cifrate (mai in chiaro).
    api_key_enc = db.Column(db.Text, nullable=True)
    api_secret_enc = db.Column(db.Text, nullable=True)
    telegram_token_enc = db.Column(db.Text, nullable=True)
    telegram_chat_id = db.Column(db.String(64), nullable=True)

    # Parametri strategia (personalizzabili solo per VIP / Lifetime).
    risk_per_trade = db.Column(db.Float, default=2.0)      # % del capitale per trade
    fast_ma = db.Column(db.Integer, default=5)             # media mobile veloce
    slow_ma = db.Column(db.Integer, default=20)            # media mobile lenta
    trading_enabled = db.Column(db.Boolean, default=True)  # motore demo (paper) attivo
    strategy = db.Column(db.String(20), default="bilanciata")  # prudente/bilanciata/aggressiva
    signal_symbols = db.Column(db.Text, nullable=True)     # crypto scelte (vuoto = tutte)

    # --- TRADING REALE con soldi veri sul conto Kraken del cliente ---
    # SPENTO per default: va acceso a mano e con piena consapevolezza.
    live_trading = db.Column(db.Boolean, default=False)
    max_order_eur = db.Column(db.Float, default=20.0)      # tetto massimo per singolo ordine
    stop_loss_pct = db.Column(db.Float, default=8.0)       # % stop loss
    take_profit_pct = db.Column(db.Float, default=15.0)    # % take profit

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Portfolio(db.Model):
    __tablename__ = "portfolios"

    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), nullable=False)
    cash = db.Column(db.Float, nullable=False)
    starting_equity = db.Column(db.Float, nullable=False)


class Trade(db.Model):
    __tablename__ = "trades"

    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), nullable=False, index=True)
    symbol = db.Column(db.String(32), nullable=False)
    side = db.Column(db.String(8), nullable=False)  # sempre "long" in questa demo
    qty = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=True)
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(8), default="open")  # open / closed
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self, current_price: float | None = None) -> dict:
        if self.status == "open" and current_price is not None:
            live_pnl = (current_price - self.entry_price) * self.qty
        else:
            live_pnl = self.pnl
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": round(self.qty, 6),
            "entry_price": round(self.entry_price, 6),
            "exit_price": round(self.exit_price, 6) if self.exit_price else None,
            "current_price": round(current_price, 6) if current_price else None,
            "pnl": round(live_pnl, 2),
            "status": self.status,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


class EquityPoint(db.Model):
    __tablename__ = "equity_points"

    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), nullable=False, index=True)
    ts = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    equity = db.Column(db.Float, nullable=False)


class Influencer(db.Model):
    """I 5 influencer che pubblicizzano il sito. Il nome è modificabile dal
    creatore direttamente dalla tabella nel pannello Amministrazione."""

    __tablename__ = "influencers"

    slot = db.Column(db.Integer, primary_key=True)  # 1..5
    name = db.Column(db.String(120), nullable=False)
    password_enc = db.Column(db.Text, nullable=True)  # password d'accesso, cifrata
    discount_code = db.Column(db.String(60), nullable=True)   # codice sconto dell'influencer
    discount_pct = db.Column(db.Float, default=0.0)          # % di sconto del codice


class Signal(db.Model):
    """Un segnale inviato su Telegram con i tasti Investi / Non investire.

    Quando il cliente tocca "Investi", il bot cerca qui il segnale (tramite il
    callback_data del bottone) e piazza l'ordine reale sul suo Kraken.
    """

    __tablename__ = "signals"

    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), nullable=False, index=True)
    symbol = db.Column(db.String(32), nullable=False)
    side = db.Column(db.String(8), default="buy")          # buy / sell
    ref_price = db.Column(db.Float, nullable=False)         # prezzo al momento del segnale
    stop_loss_pct = db.Column(db.Float, default=8.0)
    take_profit_pct = db.Column(db.Float, default=15.0)
    max_order_eur = db.Column(db.Float, default=20.0)

    status = db.Column(db.String(16), default="pending")   # pending/executed/declined/failed/expired
    result = db.Column(db.Text, nullable=True)             # esito ordine o messaggio d'errore
    telegram_message_id = db.Column(db.String(32), nullable=True)
    outcome = db.Column(db.String(8), nullable=True)       # win / loss (track record); None = ancora aperto
    warn_loss_sent = db.Column(db.Boolean, default=False)  # avviso "sta andando in perdita" già mandato
    warn_profit_sent = db.Column(db.Boolean, default=False)  # avviso "sei molto in guadagno" già mandato
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)


class PriceAlert(db.Model):
    """Avviso di prezzo personale: 'avvisami se BTC scende sotto X'."""

    __tablename__ = "price_alerts"

    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), nullable=False, index=True)
    symbol = db.Column(db.String(32), nullable=False)
    direction = db.Column(db.String(8), default="below")   # below / above
    target = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    """Recensione lasciata da un cliente (obbligatoria una volta al mese)."""

    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey("licenses.id"), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    rating = db.Column(db.Integer, default=5)      # 1..5 stelle
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
