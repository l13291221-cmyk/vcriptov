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
    trading_enabled = db.Column(db.Boolean, default=True)

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
