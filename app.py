"""
VCriptoV — Bot di trading crypto (Flask) con paywall, licenze, impostazioni
grafiche e dashboard.

Avvio rapido:
    pip install -r requirements.txt
    python app.py
Poi apri http://127.0.0.1:5000
"""

import json
import os
import secrets
import time
from datetime import datetime, timedelta
from functools import wraps

import stripe
from werkzeug.security import check_password_hash, generate_password_hash
from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from admin import (
    ADMIN_EMAIL,
    check_admin_password,
    clear_reset_code,
    create_reset_code,
    set_admin_password,
    verify_reset_code,
)
from bot import get_engine, init_engine
from config import Config
from exchange_account import account_snapshot
from i18n import LANG_COOKIE, normalize_lang
from i18n import t as translate
from licensing import generate_key, normalize, verify_checksum
from market import MARKET_EXCHANGE, market
from notify import send_telegram
from emailer import email_configured, send_activation_email, send_email
from models import (
    AdminLog,
    EquityPoint,
    Influencer,
    InfluencerAccess,
    License,
    PlanConfig,
    PriceAlert,
    Portfolio,
    Review,
    Setting,
    Signal,
    Trade,
    db,
)
from config import load_stripe_key
from plans import (
    ALL_SYMBOLS,
    PLAN_ORDER,
    PLANS,
    STRATEGIES,
    get_plan,
    get_strategy,
    plan_symbols,
)
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
        "strategy": "VARCHAR(20) DEFAULT 'bilanciata'",
        "signal_symbols": "TEXT",
        "notify_only": "BOOLEAN DEFAULT 0",
        "welcome_sent": "BOOLEAN DEFAULT 0",
    }
    license_cols = {
        "paid": "BOOLEAN DEFAULT 0",
        "influencer_slot": "INTEGER",
        "influencer_name": "VARCHAR(120)",
        "terms_accepted": "BOOLEAN DEFAULT 0",
        "device_id": "VARCHAR(64)",
        "pending_device_id": "VARCHAR(64)",
        "device_change_requested": "BOOLEAN DEFAULT 0",
        "expires_at": "DATETIME",
        "stripe_subscription_id": "VARCHAR(120)",
        "last_review_month": "VARCHAR(7)",
        "recovery_phone": "VARCHAR(40)",
        "expiry_reminder_sent": "BOOLEAN DEFAULT 0",
        "last_summary_at": "DATETIME",
        "banned": "BOOLEAN DEFAULT 0",
        "last_report_month": "VARCHAR(7)",
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
            existing_sig = {row[1] for row in conn.execute(text("PRAGMA table_info(signals)"))}
            for col, ddl in {
                "outcome": "VARCHAR(8)",
                "warn_loss_sent": "BOOLEAN DEFAULT 0",
                "warn_profit_sent": "BOOLEAN DEFAULT 0",
            }.items():
                if col not in existing_sig:
                    conn.execute(text(f"ALTER TABLE signals ADD COLUMN {col} {ddl}"))
            existing_i = {row[1] for row in conn.execute(text("PRAGMA table_info(influencers)"))}
            for col, ddl in {
                "password_enc": "TEXT",
                "discount_code": "VARCHAR(60)",
                "discount_pct": "FLOAT DEFAULT 0",
                "discount_expires": "DATE",
                "commission_pct": "FLOAT DEFAULT 0",
                "collab_start": "DATE",
            }.items():
                if col not in existing_i:
                    conn.execute(text(f"ALTER TABLE influencers ADD COLUMN {col} {ddl}"))
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
        load_plan_overrides()

    register_routes(app)

    # Avvia il motore di trading in background.
    eng = init_engine(app)
    eng.start()

    return app


# ------------------------------------------------------------------ helpers
DEVICE_COOKIE = "vcriptov_device"
LOGOUT_COOKIE = "vcriptov_logout"   # se presente, disattiva l'auto-accesso dopo "Esci"
SUBSCRIPTION_DAYS = 30  # durata di un abbonamento mensile prima della scadenza
CREATOR_EMAIL = "assistenza.vcriptov@gmail.com"  # email di accesso/recupero del creatore


_plans_loaded_at = 0.0

# Cache dello snapshot del conto Kraken, per non interrogarlo a ogni refresh
# (altrimenti la schermata va a scatti). Vedi /api/account.
_account_cache: dict = {}
ACCOUNT_TTL = 20      # secondi: riusa lo stesso snapshot
ACCOUNT_GRACE = 180   # secondi: durante un errore mostra l'ultimo saldo valido


def load_plan_overrides():
    """Applica al dizionario PLANS i prezzi e le funzioni personalizzati dal
    creatore (salvati in PlanConfig). Così get_plan() e il paywall usano subito
    i valori modificati, senza toccare il codice."""
    try:
        def _clean(v):
            # Mostra 39 invece di 39.0 quando il prezzo è intero.
            if v is None:
                return None
            return int(v) if float(v).is_integer() else v

        for pc in PlanConfig.query.all():
            p = PLANS.get(pc.plan_id)
            if not p:
                continue
            if pc.price_eur is not None:
                p["price_eur"] = _clean(pc.price_eur)
            p["old_price_eur"] = _clean(pc.old_price_eur)
            if pc.features:
                p["features"] = [ln.strip() for ln in pc.features.splitlines() if ln.strip()]
            if pc.features_en:
                p["features_en"] = [ln.strip() for ln in pc.features_en.splitlines() if ln.strip()]
    except Exception:
        db.session.rollback()


def is_expired(lic) -> bool:
    return bool(lic and lic.expires_at and datetime.utcnow() > lic.expires_at)


# ---- Protezione anti "indovina la password" (brute force) ----
_login_fails: dict[str, list] = {}
LOGIN_MAX_FAILS = 5
LOGIN_WINDOW = 900  # 15 minuti


def _client_ip() -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() if fwd else request.remote_addr) or "?"


def login_blocked(bucket: str) -> bool:
    now = time.time()
    fails = [t for t in _login_fails.get(bucket, []) if now - t < LOGIN_WINDOW]
    _login_fails[bucket] = fails
    return len(fails) >= LOGIN_MAX_FAILS


def record_login_fail(bucket: str) -> None:
    _login_fails.setdefault(bucket, []).append(time.time())


def reset_login_fails(bucket: str) -> None:
    _login_fails.pop(bucket, None)


# Anti-abuso pagamenti: limita quanti tentativi di checkout può fare lo stesso IP,
# per bloccare chi prova tante carte/email di fila (card testing / frodi).
_checkout_hits: dict[str, list] = {}
CHECKOUT_MAX = 8
CHECKOUT_WINDOW = 3600  # 1 ora


def checkout_rate_limited(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _checkout_hits.get(ip, []) if now - t < CHECKOUT_WINDOW]
    _checkout_hits[ip] = hits
    return len(hits) >= CHECKOUT_MAX


def record_checkout_hit(ip: str) -> None:
    _checkout_hits.setdefault(ip, []).append(time.time())


def needs_monthly_review(lic) -> bool:
    """True se il cliente deve lasciare la recensione di questo mese."""
    if session.get("is_admin") or session.get("is_influencer"):
        return False
    return lic and lic.last_review_month != datetime.utcnow().strftime("%Y-%m")


def get_or_make_device_id() -> str:
    """Identificativo del dispositivo (browser), salvato in un cookie. Serve a
    legare un codice a un solo dispositivo ed evitare che venga condiviso."""
    did = request.cookies.get(DEVICE_COOKIE)
    return did if did else secrets.token_hex(16)


def set_device_cookie(response, device_id: str):
    response.set_cookie(
        DEVICE_COOKIE, device_id, max_age=60 * 60 * 24 * 365,
        httponly=True, samesite="Lax",
    )
    response.delete_cookie(LOGOUT_COOKIE)  # rientrato: riattivo l'auto-accesso
    return response


def clear_logout(response):
    response.delete_cookie(LOGOUT_COOKIE)
    return response


def current_license():
    lic_id = session.get("license_id")
    if not lic_id:
        return None
    return db.session.get(License, lic_id)


def log_admin(action: str, email: str | None = None, detail: str | None = None):
    """Registra un'azione del creatore nel log di sicurezza (best-effort)."""
    try:
        db.session.add(AdminLog(action=action, target_email=email, detail=detail))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _monthly_value(plan_dict) -> float | None:
    """Valore MENSILE di un piano per il calcolo commissioni. I piani annuali
    valgono price/12 al mese; i Lifetime (pagamento unico) tornano None e vengono
    contati una volta sola (nel mese d'iscrizione)."""
    if not plan_dict:
        return 0.0
    if plan_dict.get("lifetime"):
        return None
    per_year = 12 if plan_dict.get("interval") == "year" else 1
    return (plan_dict.get("price_eur") or 0) / per_year


def influencer_payout(inf) -> dict:
    """Calcola quanto il creatore deve all'influencer.

    Ogni MESE, per ogni utente ancora abbonato e pagante arrivato da lui (dopo la
    data d'inizio collaborazione), l'influencer prende la sua percentuale su quanto
    l'utente paga quel mese. Se l'utente disdice, smette di contare."""
    from collections import OrderedDict

    pct = (inf.commission_pct or 0) / 100.0
    start = inf.collab_start
    now = datetime.utcnow()
    cur_month = now.strftime("%Y-%m")

    subs = [
        s for s in License.query.filter_by(influencer_slot=inf.slot, paid=True).all()
        if not s.email.endswith("@vcriptov.local")
        and (not start or (s.created_at and s.created_at.date() >= start))
    ]
    active_now = [s for s in subs if s.active and not is_expired(s) and not s.banned]
    users_month = [s for s in subs if s.created_at and s.created_at.strftime("%Y-%m") == cur_month]

    # Da pagare QUESTO mese: la % su ogni abbonato attivo adesso.
    owed_month = 0.0
    for s in active_now:
        p = get_plan(s.plan)
        mv = _monthly_value(p)
        if mv is None:  # Lifetime: conta solo nel mese in cui si è iscritto
            if s.created_at and s.created_at.strftime("%Y-%m") == cur_month:
                owed_month += (p.get("price_eur") or 0) * pct
        else:
            owed_month += mv * pct

    # Stima TOTALE dall'inizio: mesi di abbonamento × valore mensile × %.
    total = 0.0
    for s in subs:
        p = get_plan(s.plan)
        mv = _monthly_value(p)
        if not s.created_at:
            continue
        s_start = s.created_at.date()
        if start and start > s_start:
            s_start = start
        if mv is None:
            total += (p.get("price_eur") or 0) * pct
        else:
            end = now.date()
            if s.expires_at and s.expires_at.date() < end:
                end = s.expires_at.date()
            months = (end.year - s_start.year) * 12 + (end.month - s_start.month) + 1
            total += max(0, months) * mv * pct

    # Grafico: utenti portati per mese (ultimi 6 mesi).
    by_month = OrderedDict()
    today = now.replace(day=1)
    for k in range(5, -1, -1):
        y = today.year + (today.month - 1 - k) // 12
        m = (today.month - 1 - k) % 12 + 1
        by_month[f"{m:02d}/{y}"] = 0
    for s in subs:
        if s.created_at:
            lbl = s.created_at.strftime("%m/%Y")
            if lbl in by_month:
                by_month[lbl] += 1

    return {
        "name": inf.name,
        "slot": inf.slot,
        "pct": inf.commission_pct or 0,
        "collab_start": start.strftime("%d/%m/%Y") if start else None,
        "users_month": len(users_month),
        "users_active": len(active_now),
        "users_total": len(subs),
        "owed_month": round(owed_month, 2),
        "owed_total": round(total, 2),
        "by_month": dict(by_month),
    }


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        lic = current_license()
        if not lic or not lic.active or not lic.activated or lic.banned:
            session.clear()
            return redirect(url_for("index"))
        ep = request.endpoint
        # Prima chiedi da quale influencer arriva, poi l'accettazione dei termini.
        if lic.influencer_slot is None and ep not in ("choose_influencer", "logout"):
            return redirect(url_for("choose_influencer"))
        if not lic.terms_accepted and ep not in ("terms", "choose_influencer", "logout"):
            return redirect(url_for("terms"))
        # Abbonamento scaduto → accesso bloccato del tutto (tranne la pagina scadenza).
        if is_expired(lic) and ep not in ("expired", "logout"):
            return redirect(url_for("expired"))
        # Recensione mensile obbligatoria per continuare.
        if needs_monthly_review(lic) and ep not in ("review", "expired", "logout"):
            return redirect(url_for("review"))
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

    @app.before_request
    def _refresh_plans():
        # Ricarica i prezzi/funzioni personalizzati ogni tanto, così anche più
        # processi restano allineati dopo una modifica (senza query a ogni click).
        global _plans_loaded_at
        now = time.time()
        if now - _plans_loaded_at > 15:
            load_plan_overrides()
            _plans_loaded_at = now

    @app.context_processor
    def inject_globals():
        lang = normalize_lang(request.cookies.get(LANG_COOKIE))
        return {
            "now": datetime.utcnow(), "plans": PLANS, "asset_v": ASSET_VERSION,
            "is_admin": session.get("is_admin", False),
            "is_influencer": session.get("is_influencer", False),
            "lang": lang,
            "t": lambda key: translate(lang, key),
        }

    @app.route("/lang/<code>")
    def set_language(code):
        """Cambia lingua (it/en) salvandola in un cookie e torna alla pagina di prima."""
        resp = redirect(request.referrer or url_for("index"))
        resp.set_cookie(LANG_COOKIE, normalize_lang(code), max_age=60 * 60 * 24 * 365, samesite="Lax")
        return resp

    # ---------- Paywall / scelta piano ----------
    @app.route("/")
    def index():
        if current_license():
            return redirect(url_for("dashboard"))
        # Auto-accesso dal dispositivo già registrato: chi ha già attivato su
        # QUESTO dispositivo rientra senza reinserire il codice — SALVO che abbia
        # appena premuto "Esci" (in quel caso resta fuori finché non rientra).
        did = request.cookies.get(DEVICE_COOKIE)
        if did and not request.cookies.get(LOGOUT_COOKIE):
            lic = (
                License.query.filter_by(device_id=did, active=True, activated=True, banned=False)
                .order_by(License.activated_at.desc())
                .first()
            )
            if lic:
                session["license_id"] = lic.id
                return redirect(url_for("dashboard"))
        # Testimonianze positive (social proof) sotto i piani.
        reviews = (
            Review.query.filter(Review.rating >= 4, Review.text.isnot(None), Review.text != "")
            .order_by(Review.created_at.desc()).limit(6).all()
        )
        return render_template(
            "paywall.html",
            plans=[PLANS[p] for p in PLAN_ORDER],
            reviews=reviews,
        )

    @app.route("/come-funziona")
    def how_it_works():
        return render_template("how_it_works.html")

    @app.route("/checkout", methods=["POST"])
    def checkout():
        """Avvia un pagamento REALE tramite Stripe Checkout.

        La licenza viene creata subito ma resta DISATTIVATA (active=False):
        diventa valida solo dopo la conferma del pagamento (rotta di successo).
        """
        # Anti-frode: blocca chi tenta troppi pagamenti di fila dallo stesso IP.
        ip = _client_ip()
        if checkout_rate_limited(ip):
            flash("Troppi tentativi di pagamento. Riprova tra un'ora o contatta l'assistenza.", "error")
            return redirect(url_for("index"))
        record_checkout_hit(ip)

        email = (request.form.get("email") or "").strip().lower()
        plan_id = (request.form.get("plan") or "").strip()
        plan = get_plan(plan_id)

        if not email or "@" not in email:
            flash("Inserisci un indirizzo email valido.", "error")
            return redirect(url_for("index"))
        if not plan:
            flash("Piano non valido.", "error")
            return redirect(url_for("index"))

        # Codice sconto influencer (facoltativo): applica lo sconto e attribuisce
        # automaticamente l'utente a quell'influencer.
        code_in = (request.form.get("discount_code") or "").strip()
        inf_match = None
        if code_in:
            inf_match = next(
                (i for i in Influencer.query.all()
                 if i.discount_code and i.discount_code.strip().lower() == code_in.lower()),
                None,
            )
            if not inf_match:
                flash("Codice sconto non valido.", "error")
                return redirect(url_for("index"))
            if inf_match.discount_expires and inf_match.discount_expires < datetime.utcnow().date():
                flash("Questo codice sconto è scaduto.", "error")
                return redirect(url_for("index"))
        disc = max(0.0, min(inf_match.discount_pct or 0.0, 100.0)) if inf_match else 0.0

        def attribute(lic):
            if inf_match:
                lic.influencer_slot = inf_match.slot
                lic.influencer_name = inf_match.name

        # PROVA GRATUITA: nessun pagamento, accesso completo per pochi giorni.
        if plan.get("trial"):
            if License.query.filter_by(email=email, plan="trial").first():
                flash("Hai già usato la prova gratuita con questa email.", "error")
                return redirect(url_for("index"))
            key = generate_key(email, plan_id)
            lic = License(
                email=email, plan=plan_id, key=key, active=True, activated=False,
                expires_at=datetime.utcnow() + timedelta(days=plan.get("trial_days", 3)),
            )
            attribute(lic)
            db.session.add(lic)
            db.session.commit()
            send_activation_email(email, plan["name"], key)
            return render_template(
                "checkout.html", plan=plan, email=email, license_key=key, demo=True, trial=True
            )

        if not stripe.api_key:
            # MODALITÀ DEMO: nessuna chiave Stripe valida configurata.
            key = generate_key(email, plan_id)
            lic = License(email=email, plan=plan_id, key=key, active=True, activated=False)
            attribute(lic)
            db.session.add(lic)
            db.session.commit()
            send_activation_email(email, plan["name"], key)
            return render_template(
                "checkout.html", plan=plan, email=email, license_key=key, demo=True,
                discount=disc, influencer=(inf_match.name if inf_match else None),
            )

        # Licenza pre-creata ma non attiva finché il pagamento non è confermato.
        key = generate_key(email, plan_id)
        lic = License(email=email, plan=plan_id, key=key, active=False, activated=False)
        attribute(lic)
        db.session.add(lic)
        db.session.commit()

        # Prezzo scontato (in centesimi), mai sotto zero.
        cents = int(round(plan["price_eur"] * (1 - disc / 100.0) * 100))
        name = f"VCriptoV — Piano {plan['name']}"
        if disc:
            name += f" (sconto {disc:.0f}%)"
        price_data = {
            "currency": "eur",
            "product_data": {"name": name},
            "unit_amount": max(cents, 0),
        }
        if not plan["lifetime"]:
            price_data["recurring"] = {"interval": plan.get("interval", "month")}

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
        sub_id = cs.get("subscription")
        if sub_id:
            lic.stripe_subscription_id = sub_id
        # Piani mensili: scadenza tra ~31 giorni (i rinnovi la estendono via webhook).
        if not get_plan(lic.plan)["lifetime"]:
            lic.expires_at = datetime.utcnow() + timedelta(days=get_plan(lic.plan).get("days", SUBSCRIPTION_DAYS) + 1)
        db.session.commit()
        send_activation_email(lic.email, get_plan(lic.plan)["name"], lic.key)

        return render_template(
            "checkout.html",
            plan=get_plan(lic.plan),
            email=lic.email,
            license_key=lic.key,
        )

    @app.route("/disdici", methods=["POST"])
    @login_required
    def cancel_subscription_user():
        """L'utente disdice il RINNOVO automatico. Con cancel_at_period_end
        mantiene l'accesso fino alla fine del periodo già pagato; alla scadenza
        Stripe manda 'customer.subscription.deleted' e l'accesso si blocca."""
        lic = current_license()
        if not lic.stripe_subscription_id:
            flash("Nessun rinnovo automatico attivo da disdire su questo account.", "error")
            return redirect(url_for("settings_view"))
        try:
            stripe.Subscription.modify(lic.stripe_subscription_id, cancel_at_period_end=True)
            flash(
                "Rinnovo automatico disdetto. Manterrai l'accesso fino alla "
                "scadenza già pagata, poi non verrà più addebitato nulla.", "success",
            )
        except Exception as exc:  # noqa: BLE001
            app.logger.error("Errore disdetta Stripe: %s", exc)
            flash("Non è stato possibile disdire adesso. Riprova o scrivi all'assistenza.", "error")
        return redirect(url_for("settings_view"))

    @app.route("/checkout/cancel")
    def checkout_cancel():
        flash("Pagamento annullato. Puoi riprovare quando vuoi.", "error")
        return redirect(url_for("index"))

    @app.route("/stripe/webhook", methods=["POST"])
    def stripe_webhook():
        """Riceve gli eventi Stripe: ogni pagamento mensile riuscito ESTENDE la
        scadenza; una disdetta/mancato pagamento la fa scadere subito."""
        payload = request.get_data()
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        try:
            if secret:
                event = stripe.Webhook.construct_event(
                    payload, request.headers.get("Stripe-Signature", ""), secret
                )
            else:
                event = json.loads(payload or b"{}")
        except Exception:
            return "", 400

        etype = event.get("type", "")
        obj = (event.get("data") or {}).get("object") or {}

        # Conferma ROBUSTA del primo pagamento: attiva la licenza anche se il
        # cliente ha chiuso il browser prima di tornare sul sito.
        if etype == "checkout.session.completed":
            if obj.get("payment_status") == "paid":
                lic = db.session.get(License, int(obj.get("client_reference_id") or 0))
                if lic and not lic.paid:
                    lic.active = True
                    lic.paid = True
                    if obj.get("subscription"):
                        lic.stripe_subscription_id = obj.get("subscription")
                    if not get_plan(lic.plan)["lifetime"]:
                        lic.expires_at = datetime.utcnow() + timedelta(days=get_plan(lic.plan).get("days", SUBSCRIPTION_DAYS) + 1)
                    db.session.commit()
                    send_activation_email(lic.email, get_plan(lic.plan)["name"], lic.key)
            return "", 200

        if etype == "invoice.paid":
            sub_id = obj.get("subscription")
            lic = License.query.filter_by(stripe_subscription_id=sub_id).first() if sub_id else None
            if lic:
                base = max(lic.expires_at or datetime.utcnow(), datetime.utcnow())
                lic.expires_at = base + timedelta(days=get_plan(lic.plan).get("days", SUBSCRIPTION_DAYS) + 1)
                lic.active = True
                lic.expiry_reminder_sent = False  # rinnovato: potrà riavvisare al prossimo giro
                db.session.commit()
        elif etype in ("customer.subscription.deleted", "invoice.payment_failed"):
            sub_id = obj.get("id") if etype.startswith("customer") else obj.get("subscription")
            lic = License.query.filter_by(stripe_subscription_id=sub_id).first() if sub_id else None
            if lic:
                lic.expires_at = datetime.utcnow()  # scaduto adesso → bloccato
                db.session.commit()
        return "", 200

    @app.route("/expired")
    @login_required
    def expired():
        lic = current_license()
        return render_template("expired.html", license=lic, plan=get_plan(lic.plan))

    @app.route("/review", methods=["GET", "POST"])
    @login_required
    def review():
        lic = current_license()
        if not needs_monthly_review(lic):
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            try:
                rating = max(1, min(int(request.form.get("rating", 5)), 5))
            except (ValueError, TypeError):
                rating = 5
            text = (request.form.get("text") or "").strip()[:1000]
            db.session.add(Review(license_id=lic.id, email=lic.email, rating=rating, text=text))
            lic.last_review_month = datetime.utcnow().strftime("%Y-%m")
            db.session.commit()
            flash("Grazie per la recensione!", "success")
            return redirect(url_for("dashboard"))
        return render_template("review.html", license=lic, plan=get_plan(lic.plan))

    # ---------- Attivazione licenza ----------
    @app.route("/activate", methods=["GET", "POST"])
    def activate():
        if request.method == "POST":
            key = normalize(request.form.get("license_key") or "")
            lic = License.query.filter_by(key=key).first()

            if not lic or not lic.active:
                flash("Codice di attivazione non valido o disattivato.", "error")
                return redirect(url_for("activate"))

            if lic.banned:
                flash("Questo account è stato bloccato. Contatta l'assistenza.", "error")
                return redirect(url_for("activate"))

            # Doppio controllo: il checksum deve combaciare con email+piano.
            if not verify_checksum(lic.email, lic.plan, key):
                flash("Codice di attivazione corrotto.", "error")
                return redirect(url_for("activate"))

            # ANTI-CONDIVISIONE: il codice è legato al primo dispositivo.
            device_id = get_or_make_device_id()
            if lic.device_id and lic.device_id != device_id:
                # Registro la richiesta: comparirà un avviso nell'area creatore,
                # e memorizzo questo dispositivo così un eventuale "Sblocca" lo
                # autorizza direttamente (senza reinserire il codice).
                lic.pending_device_id = device_id
                lic.device_change_requested = True
                db.session.commit()
                flash(
                    "Questo codice è già in uso su un altro dispositivo. Contatta "
                    "l'assistenza per farti sbloccare l'accesso da qui.", "error",
                )
                # Salvo il cookie anche ora, così dopo lo sblocco entri da solo.
                return set_device_cookie(redirect(url_for("activate")), device_id)

            if not lic.device_id:
                lic.device_id = device_id  # primo dispositivo → lo lego qui
            # Il dispositivo legittimo entra: annullo eventuali richieste pendenti.
            lic.device_change_requested = False
            lic.pending_device_id = None
            if not lic.activated:
                lic.activated = True
                lic.activated_at = datetime.utcnow()
            # Piani a tempo: parte il conto alla rovescia (30 giorni mensile, 365 annuale).
            if not get_plan(lic.plan)["lifetime"] and lic.expires_at is None:
                lic.expires_at = datetime.utcnow() + timedelta(
                    days=get_plan(lic.plan).get("days", SUBSCRIPTION_DAYS))
            # Non chiedo la recensione nel mese di iscrizione (parte dal successivo).
            if lic.last_review_month is None:
                lic.last_review_month = datetime.utcnow().strftime("%Y-%m")
            if lic.settings is None:
                db.session.add(Setting(license_id=lic.id, contact_email=lic.email))
            db.session.commit()

            session.clear()
            session["license_id"] = lic.id
            flash(f"Benvenuto! Piano {get_plan(lic.plan)['name']} attivato.", "success")
            # Prima di entrare, chiediamo da quale influencer arriva.
            dest = url_for("choose_influencer") if lic.influencer_slot is None else url_for("dashboard")
            return set_device_cookie(redirect(dest), device_id)

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
        # Segno l'uscita, così l'auto-accesso dal dispositivo non ti rilogga subito.
        resp = redirect(url_for("index"))
        resp.set_cookie(LOGOUT_COOKIE, "1", max_age=60 * 60 * 24 * 365,
                        httponly=True, samesite="Lax")
        return resp

    # ---------- Area creatore (admin) ----------
    def _grant_admin():
        lic = ensure_admin_license()
        session.clear()
        session["license_id"] = lic.id
        session["is_admin"] = True
        return clear_logout(redirect(url_for("admin")))

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            bucket = "admin:" + _client_ip()
            if login_blocked(bucket):
                flash("Troppi tentativi falliti. Riprova tra qualche minuto.", "error")
                return redirect(url_for("admin_login"))
            email = (request.form.get("email") or "").strip().lower()
            # Il creatore accede con la SUA email (dell'assistenza) + password.
            if email == CREATOR_EMAIL and check_admin_password(request.form.get("password", "")):
                reset_login_fails(bucket)
                # Verifica in 2 passaggi: se l'email è configurata, mando un codice.
                if email_configured():
                    code = f"{secrets.randbelow(1_000_000):06d}"
                    session["pending_2fa"] = {
                        "hash": generate_password_hash(code), "exp": time.time() + 600,
                    }
                    if send_email(CREATOR_EMAIL, "VCriptoV — Codice di accesso",
                                  f"Il tuo codice di accesso è: {code}\nValido 10 minuti."):
                        return redirect(url_for("admin_2fa"))
                    session.pop("pending_2fa", None)  # invio fallito → entra comunque
                return _grant_admin()
            record_login_fail(bucket)
            flash("Email o password errate.", "error")
            return redirect(url_for("admin_login"))
        return render_template("admin_login.html", creator_email=CREATOR_EMAIL)

    @app.route("/admin/2fa", methods=["GET", "POST"])
    def admin_2fa():
        pend = session.get("pending_2fa")
        if not pend:
            return redirect(url_for("admin_login"))
        if request.method == "POST":
            if time.time() > float(pend.get("exp", 0)):
                session.pop("pending_2fa", None)
                flash("Codice scaduto: rifai il login.", "error")
                return redirect(url_for("admin_login"))
            if check_password_hash(pend.get("hash", ""), (request.form.get("code") or "").strip()):
                session.pop("pending_2fa", None)
                return _grant_admin()
            flash("Codice errato.", "error")
            return redirect(url_for("admin_2fa"))
        return render_template("admin_2fa.html", creator_email=CREATOR_EMAIL)

    @app.route("/admin/forgot", methods=["GET", "POST"])
    def admin_forgot():
        if request.method == "POST":
            if not email_configured():
                flash(
                    "L'invio email non è configurato: usa il metodo con il file "
                    "instance/admin_password.txt, oppure imposta le variabili SMTP.",
                    "error",
                )
                return redirect(url_for("admin_forgot"))
            code = create_reset_code()
            send_email(
                CREATOR_EMAIL, "VCriptoV — Codice reset password",
                f"Il tuo codice per reimpostare la password del creatore è:\n\n"
                f"    {code}\n\nValido 15 minuti. Se non l'hai richiesto, ignora questa email.",
            )
            flash(f"Codice inviato a {CREATOR_EMAIL}. Controlla la posta.", "success")
            return redirect(url_for("admin_reset"))
        return render_template("admin_forgot.html", creator_email=CREATOR_EMAIL,
                               email_ok=email_configured())

    @app.route("/admin/reset", methods=["GET", "POST"])
    def admin_reset():
        if request.method == "POST":
            code = (request.form.get("code") or "").strip()
            new_pw = (request.form.get("new_password") or "").strip()
            if len(new_pw) < 6:
                flash("La nuova password deve avere almeno 6 caratteri.", "error")
                return redirect(url_for("admin_reset"))
            if verify_reset_code(code):
                set_admin_password(new_pw)
                clear_reset_code()
                flash("Password aggiornata! Ora accedi con la nuova password.", "success")
                return redirect(url_for("admin_login"))
            flash("Codice non valido o scaduto.", "error")
            return redirect(url_for("admin_reset"))
        return render_template("admin_reset.html")

    @app.route("/influencer/login", methods=["GET", "POST"])
    def influencer_login():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            pw = (request.form.get("password") or "").strip()
            phone = (request.form.get("phone") or "").strip()
            if not phone:
                flash("Inserisci il tuo numero di telefono per accedere.", "error")
                return redirect(url_for("influencer_login"))
            match = None
            for inf in Influencer.query.all():
                if inf.name.strip().lower() == name.lower() and inf.password_enc:
                    if decrypt(inf.password_enc) == pw and pw:
                        match = inf
                        break
            if match:
                lic = ensure_influencer_license(match.slot)
                lic.recovery_phone = phone[:40]  # telefono per il recupero
                # Cronologia accessi: salva nome + telefono. Niente doppioni per
                # la stessa coppia nome+telefono; i vecchi restano anche se in
                # seguito rinomini lo slot.
                already = InfluencerAccess.query.filter_by(
                    name=match.name, phone=phone[:40]
                ).first()
                if not already:
                    db.session.add(InfluencerAccess(
                        slot=match.slot, name=match.name, phone=phone[:40]))
                db.session.commit()
                session.clear()
                session["license_id"] = lic.id
                session["is_influencer"] = True
                session["influencer_slot"] = match.slot
                flash(f"Benvenuto/a {match.name}! Accesso anteprima attivo.", "success")
                return clear_logout(redirect(url_for("dashboard")))
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
            {"slot": i.slot, "name": i.name, "password": decrypt(i.password_enc),
             "code": i.discount_code or "", "pct": i.discount_pct or 0,
             "expires": i.discount_expires.strftime("%Y-%m-%d") if i.discount_expires else "",
             "commission": i.commission_pct or 0,
             "collab": i.collab_start.strftime("%Y-%m-%d") if i.collab_start else ""}
            for i in inf_objs
        ]
        # Dati commissioni per il popup ⋮ di ogni influencer.
        inf_payouts = {i.slot: influencer_payout(i) for i in inf_objs}
        # Escludo gli account di servizio (creatore + anteprime influencer).
        subs = (
            License.query.filter(
                ~License.email.like("%@vcriptov.local"), License.activated == True  # noqa: E712
            )
            .order_by(License.created_at.desc())
            .all()
        )
        active = [s for s in subs if s.active]
        # VALIDI = attivi e NON scaduti: solo questi contano nei numeri/grafici,
        # così chi smette di pagare non gonfia i conteggi.
        valid = [s for s in active if not is_expired(s)]
        revenue = sum(get_plan(s.plan)["price_eur"] for s in valid if s.paid)

        # --- Guadagni STIMATI per utente dai segnali del bot (solo esiti reali) ---
        # Per ogni segnale risolto: +take_profit se a target (win), -stop_loss se in
        # perdita (loss), sull'importo del segnale. È una STIMA sui segnali.
        from collections import defaultdict
        earn = defaultdict(lambda: defaultdict(float))   # lic_id -> coin -> guadagno
        earn_sig = defaultdict(lambda: defaultdict(int))  # lic_id -> coin -> n. segnali
        for s in Signal.query.filter(Signal.outcome.isnot(None)).all():
            base = s.max_order_eur or 20.0
            g = base * (s.take_profit_pct or 0) / 100.0 if s.outcome == "win" \
                else -base * (s.stop_loss_pct or 0) / 100.0
            coin = s.symbol.replace("/USDT", "")
            earn[s.license_id][coin] += g
            earn_sig[s.license_id][coin] += 1

        # "Sta investendo ora": cripto con segnali eseguiti o in attesa negli ultimi 30gg.
        recent_cut = datetime.utcnow() - timedelta(days=30)
        investing = defaultdict(set)
        for s in Signal.query.filter(
            Signal.status.in_(("executed", "pending")), Signal.created_at >= recent_cut
        ).all():
            investing[s.license_id].add(s.symbol.replace("/USDT", ""))

        def user_earn_summary(lic_id):
            coins = earn.get(lic_id, {})
            total = round(sum(coins.values()), 2)
            ordered = sorted(coins.items(), key=lambda x: x[1], reverse=True)
            top_coin = ordered[0][0] if ordered and ordered[0][1] > 0 else None
            return total, top_coin, ordered

        # Dettaglio per il popup (⋮): andamento della persona.
        user_details = {}
        for s in active:
            total, top_coin, ordered = user_earn_summary(s.id)
            user_details[s.id] = {
                "email": s.email,
                "total": total,
                "top_coin": top_coin,
                "coins": [
                    {"coin": c, "gain": round(g, 2), "signals": earn_sig[s.id].get(c, 0)}
                    for c, g in ordered
                ],
                "investing": sorted(investing.get(s.id, [])),
            }

        # --- Grafico Amministrazione: guadagno MEDIO per utente, per cripto ---
        n_users = len(active) or 1
        coin_totals = defaultdict(float)
        for cmap in earn.values():
            for c, g in cmap.items():
                coin_totals[c] += g
        avg_by_coin = {
            c: round(v / n_users, 2)
            for c, v in sorted(coin_totals.items(), key=lambda x: x[1], reverse=True)[:8]
        }
        avg_earn_per_user = round(sum(coin_totals.values()) / n_users, 2)

        def src_name(s):
            # Nome fotografato all'iscrizione; fallback allo slot per dati vecchi.
            return s.influencer_name or influencers.get(s.influencer_slot) or "—"

        # GRAFICO: solo i 5 influencer ATTUALI (per nome corrente). Se rinomini
        # uno slot, il vecchio nome sparisce dal grafico e il nuovo parte da 0.
        current_names = [i.name for i in inf_objs]
        per_influencer = {name: 0 for name in current_names}
        per_plan = {}
        for s in valid:
            per_plan[s.plan] = per_plan.get(s.plan, 0) + 1
            if s.influencer_name in per_influencer:
                per_influencer[s.influencer_name] += 1

        rows = []
        for s in active:
            e_total, e_top, _ = user_earn_summary(s.id)
            rows.append({
                "id": s.id, "email": s.email, "plan": get_plan(s.plan)["name"],
                "price": get_plan(s.plan)["price_eur"], "paid": s.paid,
                "influencer": src_name(s),
                "device_bound": bool(s.device_id),
                "device_request": bool(s.device_change_requested),
                "expires": s.expires_at.strftime("%d/%m/%Y") if s.expires_at else "mai",
                "expired": is_expired(s),
                "date": s.created_at.strftime("%d/%m/%Y") if s.created_at else "—",
                "earn": e_total,
                "earn_coin": e_top,
                "investing": sorted(investing.get(s.id, [])),
                "banned": bool(s.banned),
            })

        # --- Statistiche più ricche ---
        # Incassi per mese (ultimi 6 mesi) dagli abbonamenti pagati.
        from collections import OrderedDict
        months = OrderedDict()
        today = datetime.utcnow().replace(day=1)
        for k in range(5, -1, -1):
            y = today.year + (today.month - 1 - k) // 12
            mth = (today.month - 1 - k) % 12 + 1
            months[f"{mth:02d}/{y}"] = 0.0
        for s in active:
            if s.paid and s.created_at:
                label = s.created_at.strftime("%m/%Y")
                if label in months:
                    months[label] += get_plan(s.plan)["price_eur"]

        # Incasso per piano.
        rev_plan = {}
        for s in active:
            if s.paid:
                nm = get_plan(s.plan)["name"]
                rev_plan[nm] = rev_plan.get(nm, 0) + get_plan(s.plan)["price_eur"]

        pending_devices = sum(1 for s in active if s.device_change_requested)

        return render_template(
            "admin.html",
            license=current_license(),
            plan=get_plan("lifetime"),
            revenue=revenue,
            active_count=len(valid),
            paid_count=sum(1 for s in valid if s.paid),
            pending_devices=pending_devices,
            per_plan={get_plan(p)["name"]: n for p, n in per_plan.items()},
            inf_access=inf_access,
            per_influencer=per_influencer,
            revenue_by_month=dict(months),
            revenue_by_plan=rev_plan,
            rows=rows,
            avg_by_coin=avg_by_coin,
            avg_earn_per_user=avg_earn_per_user,
            user_details=user_details,
            influencer_history=InfluencerAccess.query.order_by(
                InfluencerAccess.created_at.desc()).all(),
            admin_log=AdminLog.query.order_by(AdminLog.created_at.desc()).limit(50).all(),
            inf_payouts=inf_payouts,
            plan_order=[p for p in PLAN_ORDER if p != "trial"],
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
            inf.discount_code = (request.form.get(f"code_{slot}") or "").strip()[:60] or None
            try:
                inf.discount_pct = max(0.0, min(float(request.form.get(f"pct_{slot}", 0) or 0), 100.0))
            except (ValueError, TypeError):
                pass
            exp_raw = (request.form.get(f"expires_{slot}") or "").strip()
            if exp_raw:
                try:
                    inf.discount_expires = datetime.strptime(exp_raw, "%Y-%m-%d").date()
                except ValueError:
                    pass
            else:
                inf.discount_expires = None  # campo vuoto = il codice non scade
            try:
                inf.commission_pct = max(0.0, min(float(request.form.get(f"commission_{slot}", 0) or 0), 100.0))
            except (ValueError, TypeError):
                pass
            collab_raw = (request.form.get(f"collab_{slot}") or "").strip()
            if collab_raw:
                try:
                    inf.collab_start = datetime.strptime(collab_raw, "%Y-%m-%d").date()
                except ValueError:
                    pass
            else:
                inf.collab_start = None
        db.session.commit()
        flash("Influencer aggiornati (nomi, password, codici sconto).", "success")
        return redirect(url_for("admin"))

    @app.route("/admin/save-plans", methods=["POST"])
    @admin_required
    def save_plans():
        """Salva prezzi e funzioni personalizzati dei piani (dal pannello creatore)."""
        global _plans_loaded_at
        for pid in PLAN_ORDER:
            if pid == "trial":
                continue  # la prova gratuita resta gratis
            pc = db.session.get(PlanConfig, pid) or PlanConfig(plan_id=pid)
            try:
                pc.price_eur = max(0.0, float(request.form.get(f"price_{pid}", 0) or 0))
            except (ValueError, TypeError):
                pc.price_eur = None
            old_raw = (request.form.get(f"old_{pid}") or "").strip()
            try:
                pc.old_price_eur = float(old_raw) if old_raw else None
            except (ValueError, TypeError):
                pc.old_price_eur = None
            pc.features = (request.form.get(f"features_{pid}") or "").strip() or None
            # L'inglese resta quello professionale di default: il creatore scrive
            # solo in italiano, non deve tradurre nulla.
            pc.features_en = None
            db.session.add(pc)
        db.session.commit()
        load_plan_overrides()
        _plans_loaded_at = time.time()
        log_admin("edit_plans", None, "Prezzi/funzioni piani aggiornati")
        flash("Piani aggiornati! I nuovi prezzi e funzioni sono già online.", "success")
        return redirect(url_for("admin"))

    @app.route("/admin/reset-device", methods=["POST"])
    @admin_required
    def reset_device():
        """Sblocca l'accesso da un nuovo dispositivo. Se c'è una richiesta in
        attesa, autorizza QUEL dispositivo (l'utente entrerà da solo); altrimenti
        azzera il legame così potrà riattivare da zero."""
        try:
            lic = db.session.get(License, int(request.form.get("license_id", 0)))
        except (ValueError, TypeError):
            lic = None
        if lic:
            if lic.pending_device_id:
                lic.device_id = lic.pending_device_id   # autorizzo il nuovo device
                lic.pending_device_id = None
            else:
                lic.device_id = None
            lic.device_change_requested = False
            db.session.commit()
            log_admin("unlock_device", lic.email, "Sbloccato accesso da nuovo dispositivo")
            flash(f"Accesso di {lic.email} sbloccato dal nuovo dispositivo.", "success")
        return redirect(url_for("admin"))

    @app.route("/admin/extend", methods=["POST"])
    @admin_required
    def extend_subscription():
        """Estende manualmente un abbonamento di 30 giorni (rinnovo o omaggio)."""
        try:
            lic = db.session.get(License, int(request.form.get("license_id", 0)))
        except (ValueError, TypeError):
            lic = None
        if lic:
            base = max(lic.expires_at or datetime.utcnow(), datetime.utcnow())
            lic.expires_at = base + timedelta(days=SUBSCRIPTION_DAYS)
            lic.expiry_reminder_sent = False
            db.session.commit()
            log_admin("extend", lic.email, "Abbonamento esteso di 30 giorni")
            flash(f"Abbonamento di {lic.email} esteso di 30 giorni.", "success")
        return redirect(url_for("admin"))

    @app.route("/admin/ban", methods=["POST"])
    @admin_required
    def ban_user():
        """Banna (o sbanna) un utente dal sito, per sicurezza. Un utente bannato
        non può più entrare né riattivare il codice, finché non lo sbanni."""
        try:
            lic = db.session.get(License, int(request.form.get("license_id", 0)))
        except (ValueError, TypeError):
            lic = None
        if lic and lic.email != CREATOR_EMAIL:  # non bannare mai l'account creatore
            lic.banned = not lic.banned
            db.session.commit()
            if lic.banned:
                log_admin("ban", lic.email, "Utente bannato dal sito")
                flash(f"Utente {lic.email} BANNATO dal sito.", "success")
            else:
                log_admin("unban", lic.email, "Utente riammesso")
                flash(f"Utente {lic.email} riammesso.", "success")
        return redirect(url_for("admin"))

    @app.route("/admin/export.csv")
    @admin_required
    def export_users_csv():
        """Esporta la lista utenti in CSV (per contabilità / commercialista)."""
        import csv
        import io

        subs = (
            License.query.filter(~License.email.like("%@vcriptov.local"))
            .order_by(License.created_at.desc()).all()
        )
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Email", "Piano", "Prezzo EUR", "Pagato", "Bannato",
                    "Influencer", "Scadenza", "Iscritto il"])
        for s in subs:
            w.writerow([
                s.email, get_plan(s.plan)["name"], get_plan(s.plan)["price_eur"],
                "si" if s.paid else "no", "si" if s.banned else "no",
                s.influencer_name or "",
                s.expires_at.strftime("%Y-%m-%d") if s.expires_at else "mai",
                s.created_at.strftime("%Y-%m-%d") if s.created_at else "",
            ])
        fname = f"vcriptov-utenti-{datetime.utcnow():%Y%m%d}.csv"
        return Response(
            buf.getvalue(), mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={fname}"},
        )

    @app.route("/stato")
    def service_status():
        """Pagina pubblica di stato: bot, mercato e (se loggato) Telegram/Kraken."""
        eng = get_engine()
        bot_ok = bool(eng and eng.last_tick
                      and (datetime.utcnow() - eng.last_tick).total_seconds() < 180)
        prices = market.all_prices()
        market_ok = any(v for v in prices.values())
        checks = [
            {"name": "Bot di trading", "ok": bot_ok,
             "detail": "Attivo" if bot_ok else "In avvio o fermo"},
            {"name": f"Dati di mercato ({MARKET_EXCHANGE.upper()})", "ok": market_ok,
             "detail": "Prezzi in arrivo" if market_ok else "In connessione"},
            {"name": "Pagamenti (Stripe)", "ok": bool(stripe.api_key),
             "detail": "Configurato" if stripe.api_key else "Modalità demo"},
        ]
        return render_template("status.html", checks=checks,
                               all_ok=all(c["ok"] for c in checks))

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

            # --- Impostazioni segnali (piani con Telegram) ---
            if plan.get("telegram"):
                # 1) Strategia predefinita: imposta medie mobili, rischio, SL e TP.
                strat = (request.form.get("strategy") or "bilanciata").strip()
                if strat not in STRATEGIES:
                    strat = "bilanciata"
                st = get_strategy(strat)
                s.strategy = strat
                s.fast_ma, s.slow_ma = st["fast_ma"], st["slow_ma"]
                s.risk_per_trade, s.stop_loss_pct, s.take_profit_pct = st["risk"], st["sl"], st["tp"]

                # 2) Su quali crypto ricevere i segnali (vuoto = tutte quelle del piano).
                allowed = plan_symbols(lic.plan)
                chosen = [c for c in request.form.getlist("signal_symbols") if c in allowed]
                s.signal_symbols = ",".join(chosen) if chosen and len(chosen) < len(allowed) else None

                # 3) Trading reale: interruttore + tetto per ordine.
                # Modalità "solo notifiche": se accesa, il trading reale resta
                # SPENTO comunque — zero rischio, solo segnali.
                s.notify_only = request.form.get("notify_only") == "on"
                s.live_trading = (request.form.get("live_trading") == "on") and not s.notify_only
                try:
                    s.max_order_eur = max(1.0, min(float(request.form.get("max_order_eur", 20.0)), 100000.0))
                except (ValueError, TypeError):
                    flash("Importo massimo non valido, ignorato.", "error")

            # 4) Personalizzazione AVANZATA (solo VIP/Lifetime): sovrascrive la strategia.
            if plan.get("custom_strategy"):
                try:
                    s.risk_per_trade = max(0.1, min(float(request.form.get("risk_per_trade", s.risk_per_trade)), 20.0))
                    s.fast_ma = max(2, min(int(request.form.get("fast_ma", s.fast_ma)), 50))
                    s.slow_ma = max(3, min(int(request.form.get("slow_ma", s.slow_ma)), 200))
                    s.stop_loss_pct = max(0.5, min(float(request.form.get("stop_loss_pct", s.stop_loss_pct)), 90.0))
                    s.take_profit_pct = max(0.5, min(float(request.form.get("take_profit_pct", s.take_profit_pct)), 500.0))
                    if s.fast_ma >= s.slow_ma:
                        s.slow_ma = s.fast_ma + 1
                except (ValueError, TypeError):
                    flash("Parametri avanzati non validi, ignorati.", "error")

            # Messaggio di BENVENUTO guidato: la prima volta che Telegram è
            # collegato correttamente, il bot si presenta e spiega i prossimi passi.
            tok = decrypt(s.telegram_token_enc)
            if plan.get("telegram") and tok and s.telegram_chat_id and not s.welcome_sent:
                ok = send_telegram(
                    tok, s.telegram_chat_id,
                    "👋 <b>Benvenuto/a su VCriptoV!</b>\n"
                    "Telegram è collegato correttamente. 🎉\n\n"
                    "Ecco come funziona:\n"
                    "• Ti manderò qui i <b>segnali</b> con i tasti ✅ Investi / ❌ No.\n"
                    "• Se hai attivato il <b>Trading reale</b>, toccando “Investi” l'ordine "
                    "parte davvero sul tuo Kraken; altrimenti è solo informativo.\n"
                    "• Dopo che investi, <b>sorveglio la posizione</b> e ti avviso se va "
                    "molto in guadagno o in perdita.\n\n"
                    "⚠️ <i>Non è consulenza finanziaria: valuta sempre tu. Puoi impostare "
                    "la modalità “solo notifiche” per non rischiare soldi veri.</i>",
                )
                if ok:
                    s.welcome_sent = True

            db.session.commit()
            flash("Impostazioni salvate.", "success")
            return redirect(url_for("settings_view"))

        chosen = set((s.signal_symbols or "").split(",")) if s.signal_symbols else set()
        return render_template(
            "settings.html",
            license=lic,
            plan=plan,
            s=s,
            strategies=STRATEGIES,
            plan_symbol_list=plan_symbols(lic.plan),
            chosen_symbols=chosen,
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
        """Saldo e operazioni REALI dal conto Kraken del cliente (sola lettura).

        Per evitare che la schermata "vada a scatti": lo snapshot viene messo in
        cache per ~20s e, se una lettura fallisce per un intoppo momentaneo di
        Kraken, continuiamo a mostrare l'ultimo saldo valido invece di far
        sparire tutto. Così la connessione appare stabile."""
        lic = current_license()
        s = lic.settings
        now = time.time()
        c = _account_cache.get(lic.id)
        if c and now - c["ts"] < ACCOUNT_TTL:
            snap = c["result"]
        else:
            fresh = account_snapshot(s)
            prev = c or {}
            if fresh.get("connected"):
                snap = fresh
                _account_cache[lic.id] = {"ts": now, "result": fresh,
                                          "good": fresh, "good_ts": now}
            else:
                # Errore temporaneo: se avevamo un saldo valido di recente, lo
                # riproponiamo (niente flicker), altrimenti mostriamo l'errore.
                if prev.get("good") and now - prev.get("good_ts", 0) < ACCOUNT_GRACE:
                    snap = dict(prev["good"])
                    snap["stale"] = True
                else:
                    snap = fresh
                _account_cache[lic.id] = {"ts": now, "result": snap,
                                          "good": prev.get("good"),
                                          "good_ts": prev.get("good_ts", 0)}
        snap = dict(snap)
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
                "outcome": x.outcome,
                "result": x.result,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in sigs
        ])

    @app.route("/api/track")
    @login_required
    def api_track():
        """Track record dei segnali: quanti hanno raggiunto il take profit."""
        lic = current_license()
        done = Signal.query.filter(Signal.license_id == lic.id, Signal.outcome.isnot(None)).all()
        wins = sum(1 for s in done if s.outcome == "win")
        total = len(done)
        return jsonify({
            "total": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": round(wins / total * 100, 1) if total else None,
        })

    @app.route("/api/alerts", methods=["GET", "POST"])
    @login_required
    def api_alerts():
        lic = current_license()
        if request.method == "POST":
            symbol = (request.form.get("symbol") or "").strip()
            direction = (request.form.get("direction") or "below").strip()
            if symbol not in plan_symbols(lic.plan) or direction not in ("below", "above"):
                return jsonify({"ok": False, "error": "Dati non validi"}), 400
            try:
                target = float(request.form.get("target"))
            except (ValueError, TypeError):
                return jsonify({"ok": False, "error": "Prezzo non valido"}), 400
            if PriceAlert.query.filter_by(license_id=lic.id, active=True).count() >= 20:
                return jsonify({"ok": False, "error": "Troppi avvisi attivi"}), 400
            db.session.add(PriceAlert(license_id=lic.id, symbol=symbol, direction=direction, target=target))
            db.session.commit()
            return jsonify({"ok": True})
        alerts = (
            PriceAlert.query.filter_by(license_id=lic.id, active=True)
            .order_by(PriceAlert.created_at.desc()).all()
        )
        return jsonify([
            {"id": a.id, "symbol": a.symbol, "direction": a.direction, "target": a.target}
            for a in alerts
        ])

    @app.route("/api/alerts/<int:alert_id>/delete", methods=["POST"])
    @login_required
    def api_alert_delete(alert_id):
        lic = current_license()
        a = db.session.get(PriceAlert, alert_id)
        if a and a.license_id == lic.id:
            db.session.delete(a)
            db.session.commit()
        return jsonify({"ok": True})

    @app.route("/classifica")
    @login_required
    def leaderboard():
        """Classifica ANONIMA dei 10 utenti che hanno guadagnato di più con i
        segnali del bot. Guadagno = stima dai segnali chiusi (win: +take profit,
        loss: -stop loss). Mostra con quale cripto e con che metodo (rischio)."""
        from collections import defaultdict
        earn = defaultdict(lambda: defaultdict(float))
        for s in Signal.query.filter(Signal.outcome.isnot(None)).all():
            base = s.max_order_eur or 20.0
            g = base * (s.take_profit_pct or 0) / 100.0 if s.outcome == "win" \
                else -base * (s.stop_loss_pct or 0) / 100.0
            earn[s.license_id][s.symbol.replace("/USDT", "")] += g

        lics = {
            l.id: l for l in
            License.query.filter_by(active=True, activated=True, banned=False).all()
        }
        risk_key = {"prudente": "low", "bilanciata": "medium", "aggressiva": "high"}
        rows = []
        for lic_id, coins in earn.items():
            lic = lics.get(lic_id)
            if not lic or lic.email.endswith("@vcriptov.local"):
                continue
            total = sum(coins.values())
            if total <= 0:
                continue
            top = max(coins.items(), key=lambda x: x[1])[0]
            strat = (lic.settings.strategy if lic.settings else None) or "bilanciata"
            rows.append({
                # Etichetta anonima ma stabile per utente (nessun dato personale).
                "name": f"{1000 + (lic_id * 37) % 9000}",
                "gain": round(total, 2),
                "coin": top,
                "risk": risk_key.get(strat, "medium"),
            })
        rows.sort(key=lambda x: x["gain"], reverse=True)
        return render_template(
            "classifica.html",
            rows=rows[:10],
            plan=get_plan(current_license().plan),
            license=current_license(),
        )

    @app.route("/i-guadagni")
    @login_required
    def influencer_earnings():
        """Schermata guadagni per l'influencer loggato: quanto ha guadagnato questo
        mese, in totale, quanti utenti ha portato e il grafico mese per mese."""
        if not session.get("is_influencer"):
            return redirect(url_for("dashboard"))
        slot = session.get("influencer_slot")
        inf = db.session.get(Influencer, slot) if slot else None
        if not inf:
            return redirect(url_for("dashboard"))
        return render_template(
            "influencer_earnings.html",
            payout=influencer_payout(inf),
            plan=get_plan("lifetime"),
            license=current_license(),
        )

    @app.errorhandler(404)
    def not_found(e):
        # Pagina inesistente → riporta al paywall (prima pagina del sito).
        return redirect(url_for("index"))


app = create_app()


if __name__ == "__main__":
    # use_reloader=False per non avviare due volte il thread del bot.
    app.run(host="0.0.0.0", port=Config.PORT, debug=True, use_reloader=False)
