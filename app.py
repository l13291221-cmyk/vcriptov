"""
VCriptoV — Bot di trading crypto (Flask) con paywall, licenze, impostazioni
grafiche e dashboard.

Avvio rapido:
    pip install -r requirements.txt
    python app.py
Poi apri http://127.0.0.1:5000
"""

import time
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

from admin import ADMIN_EMAIL, check_admin_password
from bot import init_engine
from config import Config
from exchange_account import account_snapshot
from licensing import generate_key, normalize, verify_checksum
from market import MARKET_EXCHANGE, market
from notify import send_telegram
from models import (
    EquityPoint,
    Influencer,
    License,
    Portfolio,
    Setting,
    Signal,
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

# Versione degli asset (CSS/JS): cambia ad ogni avvio, così il browser è
# costretto a scaricare i file aggiornati e non mostra più la versione vecchia.
ASSET_VERSION = str(int(time.time()))


def ensure_schema():
    """Migrazione leggera: aggiunge al DB esistente le colonne nuove del
    trading reale (SQLite non le crea da solo su una tabella già esistente)."""
    from sqlalchemy import text

    settings_cols = {
        "live_trading": "BOOLEAN DEFAULT 0",
        "max_order_eur": "FLOAT DEFAULT 20.0",
        "stop_loss_pct": "FLOAT DEFAULT 8.0",
        "take_profit_pct": "FLOAT DEFAULT 15.0",
    }
    license_cols = {
        "paid": "BOOLEAN DEFAULT 0",
        "influencer_slot": "INTEGER",
        "influencer_name": "VARCHAR(120)",
        "terms_accepted": "BOOLEAN DEFAULT 0",
    }
    try:
        with db.engine.begin() as conn:
            existing = {row[1] for row in conn.execute(text("PRAGMA table_info(settings)"))}
            for col, ddl in settings_cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {col} {ddl}"))
            existing_l = {row[1] for row in conn.execute(text("PRAGMA table_info(licenses)"))}
            for col, ddl in license_cols.items():
                if col not in existing_l:
                    conn.execute(text(f"ALTER TABLE licenses ADD COLUMN {col} {ddl}"))
            existing_i = {row[1] for row in conn.execute(text("PRAGMA table_info(influencers)"))}
            if "password_enc" not in existing_i:
                conn.execute(text("ALTER TABLE influencers ADD COLUMN password_enc TEXT"))
    except Exception:
        # Se qualcosa va storto (es. DB nuovo), create_all ha già fatto il lavoro.
        pass

    # Crea i 5 influencer se non esistono ancora.
    try:
        for slot in range(1, 6):
            if not db.session.get(Influencer, slot):
                db.session.add(Influencer(slot=slot, name=f"Influencer {slot}"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Backfill: per le licenze esistenti senza nome influencer salvato, uso il
    # nome attuale dello slot (una tantum, best effort).
    try:
        pending = License.query.filter(
            License.influencer_slot.isnot(None), License.influencer_name.is_(None)
        ).all()
        for lic in pending:
            if 1 <= (lic.influencer_slot or 0) <= 5:
                inf = db.session.get(Influencer, lic.influencer_slot)
                lic.influencer_name = inf.name if inf else None
        if pending:
            db.session.commit()
    except Exception:
        db.session.rollback()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # non far cachare i file statici
    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_schema()

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
        ep = request.endpoint
        # Prima chiedi da quale influencer arriva, poi l'accettazione dei termini.
        if lic.influencer_slot is None and ep not in ("choose_influencer", "logout"):
            return redirect(url_for("choose_influencer"))
        if not lic.terms_accepted and ep not in ("terms", "choose_influencer", "logout"):
            return redirect(url_for("terms"))
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapper


def ensure_admin_license():
    """Crea (una volta) la licenza del creatore: accesso Lifetime gratuito."""
    lic = License.query.filter_by(email=ADMIN_EMAIL).first()
    if not lic:
        lic = License(
            email=ADMIN_EMAIL, plan="lifetime",
            key=generate_key(ADMIN_EMAIL, "lifetime"),
            active=True, activated=True, activated_at=datetime.utcnow(),
            paid=False, influencer_slot=0, terms_accepted=True,
        )
        db.session.add(lic)
        db.session.flush()
        db.session.add(Setting(license_id=lic.id, contact_email=ADMIN_EMAIL))
        db.session.commit()
    return lic


def ensure_influencer_license(slot: int):
    """Licenza di ANTEPRIMA per un influencer: accesso completo (Lifetime, demo)
    per registrare i video. Non conta come abbonato e non vede l'area creatore."""
    email = f"influencer{slot}@vcriptov.local"
    lic = License.query.filter_by(email=email).first()
    if not lic:
        lic = License(
            email=email, plan="lifetime", key=generate_key(email, "lifetime"),
            active=True, activated=True, activated_at=datetime.utcnow(),
            paid=False, influencer_slot=0, terms_accepted=True,
        )
        db.session.add(lic)
        db.session.flush()
        db.session.add(Setting(license_id=lic.id, contact_email=email))
        db.session.commit()
    return lic


# ------------------------------------------------------------------ routes
def register_routes(app: Flask):

    @app.context_processor
    def inject_globals():
        return {
            "now": datetime.utcnow(), "plans": PLANS, "asset_v": ASSET_VERSION,
            "is_admin": session.get("is_admin", False),
        }

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
            # MODALITÀ DEMO: nessuna chiave Stripe valida configurata.
            # Genera subito il codice, senza pagamento, per provare tutto il
            # sito (grafica, dashboard, impostazioni) gratis.
            key = generate_key(email, plan_id)
            lic = License(email=email, plan=plan_id, key=key, active=True, activated=False)
            db.session.add(lic)
            db.session.commit()
            return render_template(
                "checkout.html", plan=plan, email=email, license_key=key, demo=True
            )

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
            # Mostra il motivo REALE di Stripe, così l'errore è diagnosticabile.
            reason = getattr(exc, "user_message", None) or str(exc)
            app.logger.error("Errore Stripe alla creazione della sessione: %s", exc)
            flash(f"Errore Stripe: {reason}", "error")
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
        lic.paid = True  # pagamento reale confermato
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
            # Prima di entrare, chiediamo da quale influencer arriva.
            if lic.influencer_slot is None:
                return redirect(url_for("choose_influencer"))
            return redirect(url_for("dashboard"))

        return render_template("activate.html")

    @app.route("/choose-influencer", methods=["GET", "POST"])
    @login_required
    def choose_influencer():
        lic = current_license()
        if lic.influencer_slot is not None:
            return redirect(url_for("dashboard"))
        influencers = Influencer.query.order_by(Influencer.slot).all()
        if request.method == "POST":
            try:
                slot = int(request.form.get("influencer_slot", 0))
            except (ValueError, TypeError):
                slot = 0
            if 1 <= slot <= 5:
                inf = db.session.get(Influencer, slot)
                lic.influencer_slot = slot
                # Fotografo il nome ORA: un futuro rinomino non tocca lo storico.
                lic.influencer_name = inf.name if inf else f"Influencer {slot}"
                db.session.commit()
                return redirect(url_for("dashboard"))
            flash("Scegli da dove arrivi.", "error")
        return render_template("choose_influencer.html", influencers=influencers)

    @app.route("/terms", methods=["GET", "POST"])
    @login_required
    def terms():
        lic = current_license()
        if lic.terms_accepted:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            lic.terms_accepted = True
            db.session.commit()
            return redirect(url_for("dashboard"))
        return render_template("terms.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    # ---------- Area creatore (admin) ----------
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            if check_admin_password(request.form.get("password", "")):
                lic = ensure_admin_license()
                session.clear()
                session["license_id"] = lic.id
                session["is_admin"] = True
                return redirect(url_for("admin"))
            flash("Password errata.", "error")
            return redirect(url_for("admin_login"))
        return render_template("admin_login.html")

    @app.route("/influencer/login", methods=["GET", "POST"])
    def influencer_login():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            pw = (request.form.get("password") or "").strip()
            match = None
            for inf in Influencer.query.all():
                if inf.name.strip().lower() == name.lower() and inf.password_enc:
                    if decrypt(inf.password_enc) == pw and pw:
                        match = inf
                        break
            if match:
                lic = ensure_influencer_license(match.slot)
                session.clear()
                session["license_id"] = lic.id
                session["is_influencer"] = True
                flash(f"Benvenuto/a {match.name}! Accesso anteprima attivo.", "success")
                return redirect(url_for("dashboard"))
            flash("Nome o password non validi.", "error")
            return redirect(url_for("influencer_login"))
        return render_template("influencer_login.html")

    @app.route("/admin")
    @admin_required
    def admin():
        inf_objs = Influencer.query.order_by(Influencer.slot).all()
        influencers = {i.slot: i.name for i in inf_objs}
        # Nome + password (decifrata) per la tabella accessi influencer.
        inf_access = [
            {"slot": i.slot, "name": i.name, "password": decrypt(i.password_enc)}
            for i in inf_objs
        ]
        # Escludo gli account di servizio (creatore + anteprime influencer).
        subs = (
            License.query.filter(
                ~License.email.like("%@vcriptov.local"), License.activated == True  # noqa: E712
            )
            .order_by(License.created_at.desc())
            .all()
        )
        active = [s for s in subs if s.active]
        revenue = sum(get_plan(s.plan)["price_eur"] for s in active if s.paid)

        def src_name(s):
            # Nome fotografato all'iscrizione; fallback allo slot per dati vecchi.
            return s.influencer_name or influencers.get(s.influencer_slot) or "—"

        per_plan = {}
        per_influencer = {}
        for s in active:
            per_plan[s.plan] = per_plan.get(s.plan, 0) + 1
            nm = src_name(s)
            per_influencer[nm] = per_influencer.get(nm, 0) + 1

        rows = [{
            "email": s.email, "plan": get_plan(s.plan)["name"],
            "price": get_plan(s.plan)["price_eur"], "paid": s.paid,
            "influencer": src_name(s),
            "date": s.created_at.strftime("%d/%m/%Y") if s.created_at else "—",
        } for s in active]

        return render_template(
            "admin.html",
            license=current_license(),
            plan=get_plan("lifetime"),
            revenue=revenue,
            active_count=len(active),
            per_plan={get_plan(p)["name"]: n for p, n in per_plan.items()},
            inf_access=inf_access,
            per_influencer=per_influencer,
            rows=rows,
        )

    @app.route("/admin/save-influencers", methods=["POST"])
    @admin_required
    def save_influencers():
        for slot in range(1, 6):
            inf = db.session.get(Influencer, slot)
            if not inf:
                continue
            name = (request.form.get(f"name_{slot}") or "").strip()
            if name:
                inf.name = name[:120]
            # La password si aggiorna solo se il campo è stato compilato.
            pw = (request.form.get(f"password_{slot}") or "").strip()
            if pw:
                inf.password_enc = encrypt(pw)
        db.session.commit()
        flash("Influencer aggiornati (nomi e password).", "success")
        return redirect(url_for("admin"))

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

            # --- Trading reale (richiede Telegram): interruttore + protezioni ---
            if plan.get("telegram"):
                s.live_trading = request.form.get("live_trading") == "on"
                try:
                    s.max_order_eur = max(1.0, min(float(request.form.get("max_order_eur", 20.0)), 100000.0))
                    s.stop_loss_pct = max(0.5, min(float(request.form.get("stop_loss_pct", 8.0)), 90.0))
                    s.take_profit_pct = max(0.5, min(float(request.form.get("take_profit_pct", 15.0)), 500.0))
                except (ValueError, TypeError):
                    flash("Parametri di rischio non validi, ignorati.", "error")

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
                "data_source": market.source,
                "market_exchange": MARKET_EXCHANGE,
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
            ch = market.change(s)  # variazione 24h reale (o None se non disponibile)
            out.append(
                {
                    "symbol": s,
                    "price": round(prices.get(s, 0.0), 6),
                    "change": round(ch, 2) if ch is not None else None,
                }
            )
        return jsonify(out)

    @app.route("/api/telegram/test", methods=["POST"])
    @login_required
    def api_telegram_test():
        """Invia un messaggio di prova su Telegram con le impostazioni salvate,
        così il cliente verifica subito di aver collegato tutto correttamente."""
        lic = current_license()
        plan = get_plan(lic.plan)
        if not plan.get("telegram"):
            return jsonify({"ok": False, "error": "Telegram non incluso nel tuo piano."}), 403

        s = lic.settings
        token = decrypt(s.telegram_token_enc) if s else ""
        chat_id = s.telegram_chat_id if s else ""
        if not token or not chat_id:
            return jsonify(
                {"ok": False, "error": "Inserisci prima Token e Chat ID, poi salva."}
            ), 400

        ok = send_telegram(
            token,
            chat_id,
            "✅ <b>VCriptoV</b>\nCollegamento riuscito! Da ora riceverai qui i segnali del bot.",
        )
        if ok:
            return jsonify({"ok": True})
        return jsonify(
            {"ok": False, "error": "Invio fallito: controlla Token e Chat ID."}
        ), 400

    @app.route("/api/account")
    @login_required
    def api_account():
        """Saldo e operazioni REALI dal conto Kraken del cliente (sola lettura)."""
        lic = current_license()
        s = lic.settings
        snap = account_snapshot(s)
        snap["live_trading"] = bool(s and s.live_trading)
        return jsonify(snap)

    @app.route("/api/signals")
    @login_required
    def api_signals():
        """Storico dei segnali inviati e del loro esito."""
        lic = current_license()
        sigs = (
            Signal.query.filter_by(license_id=lic.id)
            .order_by(Signal.created_at.desc())
            .limit(30)
            .all()
        )
        return jsonify([
            {
                "symbol": x.symbol,
                "side": x.side,
                "ref_price": round(x.ref_price, 6),
                "sl": x.stop_loss_pct,
                "tp": x.take_profit_pct,
                "status": x.status,
                "result": x.result,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in sigs
        ])

    @app.errorhandler(404)
    def not_found(e):
        return render_template("activate.html"), 404


app = create_app()


if __name__ == "__main__":
    # use_reloader=False per non avviare due volte il thread del bot.
    app.run(host="0.0.0.0", port=Config.PORT, debug=True, use_reloader=False)
