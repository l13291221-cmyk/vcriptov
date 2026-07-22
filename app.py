"""
VCriptoV — Bot di trading crypto (Flask) con paywall, licenze, impostazioni
grafiche e dashboard.

Avvio rapido:
    pip install -r requirements.txt
    python app.py
Poi apri http://127.0.0.1:5000
"""

from datetime import datetime
from functools import wraps

import stripe
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from bot import init_engine
from config import Config
from licensing import generate_key, normalize, verify_checksum
from market import market
from models import (
    EquityPoint,
    License,
    Portfolio,
    Setting,
    Trade,
    db,
)
from config import load_stripe_key
from plans import ALL_SYMBOLS, PLAN_ORDER, PLANS, get_plan, plan_symbols
from security import decrypt, encrypt, mask

# La chiave segreta Stripe viene letta da `instance/stripe.key` (o dalla
# variabile d'ambiente STRIPE_SECRET_KEY). NON va scritta qui nel codice, che
# è versionato e finirebbe su git/GitHub. Vedi config.load_stripe_key().
stripe.api_key = load_stripe_key()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)

    # Avvia il motore di trading in background.
    eng = init_engine(app)
    eng.start()

    return app


# ------------------------------------------------------------------ helpers
def current_license():
    lic_id = session.get("license_id")
    if not lic_id:
        return None
    return db.session.get(License, lic_id)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        lic = current_license()
        if not lic or not lic.active or not lic.activated:
            session.clear()
            return redirect(url_for("activate"))
        return view(*args, **kwargs)

    return wrapper


# ------------------------------------------------------------------ routes
def register_routes(app: Flask):

    @app.context_processor
    def inject_globals():
        return {"now": datetime.utcnow(), "plans": PLANS}

    # ---------- Paywall / scelta piano ----------
    @app.route("/")
    def index():
        if current_license():
            return redirect(url_for("dashboard"))
        return render_template(
            "paywall.html",
            plans=[PLANS[p] for p in PLAN_ORDER],
        )

    @app.route("/checkout", methods=["POST"])
    def checkout():
        """Avvia un pagamento REALE tramite Stripe Checkout.

        La licenza viene creata subito ma resta DISATTIVATA (active=False):
        diventa valida solo dopo la conferma del pagamento (rotta di successo).
        """
        email = (request.form.get("email") or "").strip().lower()
        plan_id = (request.form.get("plan") or "").strip()
        plan = get_plan(plan_id)

        if not email or "@" not in email:
            flash("Inserisci un indirizzo email valido.", "error")
            return redirect(url_for("index"))
        if not plan:
            flash("Piano non valido.", "error")
            return redirect(url_for("index"))
        if not stripe.api_key:
            flash(
                "Pagamenti non configurati: incolla la tua Stripe Secret Key nel "
                "file instance/stripe.key e riavvia l'app.",
                "error",
            )
            return redirect(url_for("index"))

        # Licenza pre-creata ma non attiva finché il pagamento non è confermato.
        key = generate_key(email, plan_id)
        lic = License(email=email, plan=plan_id, key=key, active=False, activated=False)
        db.session.add(lic)
        db.session.commit()

        # Piani mensili -> abbonamento ricorrente; Lifetime -> pagamento unico.
        price_data = {
            "currency": "eur",
            "product_data": {"name": f"VCriptoV — Piano {plan['name']}"},
            "unit_amount": int(plan["price_eur"]) * 100,  # in centesimi
        }
        if not plan["lifetime"]:
            price_data["recurring"] = {"interval": "month"}

        try:
            checkout_session = stripe.checkout.Session.create(
                mode="subscription" if not plan["lifetime"] else "payment",
                customer_email=email,
                client_reference_id=str(lic.id),
                line_items=[{"price_data": price_data, "quantity": 1}],
                metadata={"license_id": str(lic.id), "plan": plan_id, "email": email},
                success_url=url_for("checkout_success", _external=True)
                + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=url_for("checkout_cancel", _external=True),
            )
        except stripe.error.StripeError as exc:
            db.session.delete(lic)
            db.session.commit()
            app.logger.error("Errore Stripe alla creazione della sessione: %s", exc)
            flash("Errore nell'avvio del pagamento. Riprova.", "error")
            return redirect(url_for("index"))

        # Reindirizza l'utente alla pagina di pagamento ospitata da Stripe.
        return redirect(checkout_session.url, code=303)

    @app.route("/checkout/success")
    def checkout_success():
        """Rotta di ritorno da Stripe: verifica il pagamento e attiva la licenza."""
        session_id = request.args.get("session_id")
        if not session_id or not stripe.api_key:
            return redirect(url_for("index"))

        try:
            cs = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as exc:
            app.logger.error("Errore Stripe nel recupero della sessione: %s", exc)
            flash("Impossibile verificare il pagamento.", "error")
            return redirect(url_for("index"))

        # Solo un pagamento effettivamente riuscito attiva la licenza.
        if cs.get("payment_status") != "paid":
            flash("Pagamento non completato.", "error")
            return redirect(url_for("index"))

        lic = db.session.get(License, int(cs.get("client_reference_id") or 0))
        if not lic:
            flash("Licenza non trovata per questo pagamento.", "error")
            return redirect(url_for("index"))

        # Idempotente: se ricarichi la pagina non si ri-attiva/duplica nulla.
        if not lic.active:
            lic.active = True
            db.session.commit()

        return render_template(
            "checkout.html",
            plan=get_plan(lic.plan),
            email=lic.email,
            license_key=lic.key,
        )

    @app.route("/checkout/cancel")
    def checkout_cancel():
        flash("Pagamento annullato. Puoi riprovare quando vuoi.", "error")
        return redirect(url_for("index"))

    # ---------- Attivazione licenza ----------
    @app.route("/activate", methods=["GET", "POST"])
    def activate():
        if request.method == "POST":
            key = normalize(request.form.get("license_key") or "")
            lic = License.query.filter_by(key=key).first()

            if not lic or not lic.active:
                flash("Codice di attivazione non valido o disattivato.", "error")
                return redirect(url_for("activate"))

            # Doppio controllo: il checksum deve combaciare con email+piano.
            if not verify_checksum(lic.email, lic.plan, key):
                flash("Codice di attivazione corrotto.", "error")
                return redirect(url_for("activate"))

            if not lic.activated:
                lic.activated = True
                lic.activated_at = datetime.utcnow()
            if lic.settings is None:
                db.session.add(Setting(license_id=lic.id, contact_email=lic.email))
            if lic.portfolio is None:
                db.session.add(
                    Portfolio(
                        license_id=lic.id,
                        cash=Config.STARTING_EQUITY,
                        starting_equity=Config.STARTING_EQUITY,
                    )
                )
            db.session.commit()

            session.clear()
            session["license_id"] = lic.id
            flash(f"Benvenuto! Piano {get_plan(lic.plan)['name']} attivato.", "success")
            return redirect(url_for("dashboard"))

        return render_template("activate.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    # ---------- Dashboard ----------
    @app.route("/dashboard")
    @login_required
    def dashboard():
        lic = current_license()
        plan = get_plan(lic.plan)
        return render_template(
            "dashboard.html",
            license=lic,
            plan=plan,
            symbols=plan_symbols(lic.plan),
        )

    # ---------- Impostazioni ----------
    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    def settings_view():
        lic = current_license()
        plan = get_plan(lic.plan)
        s = lic.settings
        if s is None:
            s = Setting(license_id=lic.id, contact_email=lic.email)
            db.session.add(s)
            db.session.commit()

        if request.method == "POST":
            s.contact_email = (request.form.get("contact_email") or "").strip()
            s.exchange = (request.form.get("exchange") or "kraken").strip()

            # Le credenziali si aggiornano solo se l'utente ha inserito qualcosa
            # (i campi mostrano un placeholder mascherato, non il valore reale).
            api_key = (request.form.get("api_key") or "").strip()
            api_secret = (request.form.get("api_secret") or "").strip()
            tg_token = (request.form.get("telegram_token") or "").strip()

            if api_key:
                s.api_key_enc = encrypt(api_key)
            if api_secret:
                s.api_secret_enc = encrypt(api_secret)
            if tg_token:
                s.telegram_token_enc = encrypt(tg_token)

            s.telegram_chat_id = (request.form.get("telegram_chat_id") or "").strip() or None
            s.trading_enabled = request.form.get("trading_enabled") == "on"

            # Parametri strategia: modificabili solo dai piani VIP/Lifetime.
            if plan.get("custom_strategy"):
                try:
                    s.risk_per_trade = max(0.1, min(float(request.form.get("risk_per_trade", 2.0)), 20.0))
                    s.fast_ma = max(2, min(int(request.form.get("fast_ma", 5)), 50))
                    s.slow_ma = max(3, min(int(request.form.get("slow_ma", 20)), 200))
                    if s.fast_ma >= s.slow_ma:
                        s.slow_ma = s.fast_ma + 1
                except (ValueError, TypeError):
                    flash("Parametri strategia non validi, ignorati.", "error")

            db.session.commit()
            flash("Impostazioni salvate.", "success")
            return redirect(url_for("settings_view"))

        return render_template(
            "settings.html",
            license=lic,
            plan=plan,
            s=s,
            masked_api_key=mask(decrypt(s.api_key_enc)),
            masked_api_secret=mask(decrypt(s.api_secret_enc)),
            masked_telegram=mask(decrypt(s.telegram_token_enc)),
        )

    # ---------- API JSON per i grafici ----------
    @app.route("/api/overview")
    @login_required
    def api_overview():
        lic = current_license()
        prices = market.all_prices()
        pf = lic.portfolio
        open_trades = Trade.query.filter_by(license_id=lic.id, status="open").all()
        positions_value = sum(t.qty * prices.get(t.symbol, t.entry_price) for t in open_trades)
        equity = (pf.cash if pf else 0.0) + positions_value
        start = pf.starting_equity if pf else Config.STARTING_EQUITY

        closed = Trade.query.filter_by(license_id=lic.id, status="closed").all()
        realized = sum(t.pnl for t in closed)
        unrealized = sum((prices.get(t.symbol, t.entry_price) - t.entry_price) * t.qty for t in open_trades)
        wins = len([t for t in closed if t.pnl > 0])
        win_rate = (wins / len(closed) * 100) if closed else 0.0

        return jsonify(
            {
                "equity": round(equity, 2),
                "cash": round(pf.cash if pf else 0.0, 2),
                "positions_value": round(positions_value, 2),
                "starting_equity": round(start, 2),
                "total_pnl": round(equity - start, 2),
                "total_pnl_pct": round((equity - start) / start * 100, 2) if start else 0.0,
                "realized_pnl": round(realized, 2),
                "unrealized_pnl": round(unrealized, 2),
                "open_positions": len(open_trades),
                "closed_trades": len(closed),
                "win_rate": round(win_rate, 1),
            }
        )

    @app.route("/api/equity")
    @login_required
    def api_equity():
        lic = current_license()
        points = (
            EquityPoint.query.filter_by(license_id=lic.id)
            .order_by(EquityPoint.ts.asc())
            .limit(500)
            .all()
        )
        return jsonify(
            {
                "labels": [p.ts.strftime("%H:%M:%S") for p in points],
                "values": [round(p.equity, 2) for p in points],
            }
        )

    @app.route("/api/positions")
    @login_required
    def api_positions():
        lic = current_license()
        prices = market.all_prices()
        open_trades = (
            Trade.query.filter_by(license_id=lic.id, status="open")
            .order_by(Trade.opened_at.desc())
            .all()
        )
        return jsonify([t.to_dict(prices.get(t.symbol)) for t in open_trades])

    @app.route("/api/trades")
    @login_required
    def api_trades():
        lic = current_license()
        closed = (
            Trade.query.filter_by(license_id=lic.id, status="closed")
            .order_by(Trade.closed_at.desc())
            .limit(50)
            .all()
        )
        return jsonify([t.to_dict() for t in closed])

    @app.route("/api/prices")
    @login_required
    def api_prices():
        lic = current_license()
        symbols = plan_symbols(lic.plan)
        prices = market.all_prices()
        out = []
        for s in symbols:
            hist = market.history(s)
            change = 0.0
            if len(hist) >= 2 and hist[-2]:
                change = (hist[-1] - hist[-2]) / hist[-2] * 100
            out.append(
                {
                    "symbol": s,
                    "price": round(prices.get(s, 0.0), 6),
                    "change": round(change, 3),
                    "spark": [round(x, 6) for x in hist[-40:]],
                }
            )
        return jsonify(out)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("activate.html"), 404


app = create_app()


if __name__ == "__main__":
    # use_reloader=False per non avviare due volte il thread del bot.
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
