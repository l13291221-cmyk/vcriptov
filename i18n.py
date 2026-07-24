"""
Traduzioni IT/EN. La lingua è salvata in un cookie ('lang'); se manca, italiano.
Per tradurre una pagina si usa `t("chiave")` nei template (vedi context_processor
in app.py). Le chiavi mancanti ricadono sull'italiano, così non si rompe nulla.
"""

LANG_COOKIE = "vcriptov_lang"
SUPPORTED = ("it", "en")


def normalize_lang(code: str | None) -> str:
    code = (code or "").lower()[:2]
    return code if code in SUPPORTED else "it"


TRANSLATIONS = {
    # --- comune / navigazione ---
    "nav_support": {"it": "🎧 Assistenza", "en": "🎧 Support"},
    "nav_influencer": {"it": "📣 Influencer", "en": "📣 Influencer"},
    "nav_creator": {"it": "🔐 Area creatore", "en": "🔐 Creator area"},
    "nav_how": {"it": "📘 Come funziona", "en": "📘 How it works"},
    "nav_dashboard": {"it": "📊 Dashboard", "en": "📊 Dashboard"},
    "nav_settings": {"it": "⚙️ Impostazioni", "en": "⚙️ Settings"},
    "nav_leaderboard": {"it": "🏆 Classifica", "en": "🏆 Leaderboard"},
    "nav_admin": {"it": "👑 Amministrazione", "en": "👑 Administration"},
    "nav_logout": {"it": "🚪 Esci", "en": "🚪 Log out"},
    "support_need": {"it": "Hai bisogno di aiuto? Contattaci.",
                     "en": "Need help? Get in touch."},

    # --- paywall / landing ---
    "tagline": {"it": "Trading bot automatizzato per criptovalute",
                "en": "Automated crypto trading bot"},
    "hero_title": {"it": "Sblocca il tuo bot di trading",
                   "en": "Unlock your trading bot"},
    "hero_lead": {
        "it": "Scegli un piano per attivare la dashboard, i segnali automatici e il "
              "motore di trading in background. Riceverai subito un ",
        "en": "Choose a plan to unlock the dashboard, automatic signals and the "
              "background trading engine. You'll instantly receive an ",
    },
    "hero_code": {"it": "codice di attivazione", "en": "activation code"},
    "hero_lead_end": {"it": " da inserire per accedere. ",
                      "en": " to enter and get access. "},
    "badge_popular": {"it": "PIÙ SCELTO", "en": "MOST POPULAR"},
    "per": {"it": "/", "en": "/"},
    "period_lifetime": {"it": "Pagamento unico, accesso a vita",
                        "en": "One-time payment, lifetime access"},
    "period_recurring": {"it": "Rinnovo automatico, disdici quando vuoi",
                         "en": "Auto-renews, cancel anytime"},
    "email_ph": {"it": "La tua email (es. mario@rossi.it)",
                 "en": "Your email (e.g. john@doe.com)"},
    "discount_ph": {"it": "Codice sconto (facoltativo)",
                    "en": "Discount code (optional)"},
    "proceed": {"it": "Procedi e genera il codice →",
                "en": "Continue and generate my code →"},
    "disclaimer": {
        "it": "⚠️ <strong>Avviso:</strong> i segnali del bot sono <strong>analisi "
              "automatiche non accurate al 100%</strong> e <strong>non costituiscono "
              "consulenza finanziaria</strong>: controlla sempre di persona ogni "
              "investimento e non affidarti ciecamente al bot. Investendo rischi il "
              "tuo capitale. I pagamenti sono gestiti da <strong>Stripe</strong>.",
        "en": "⚠️ <strong>Disclaimer:</strong> the bot's signals are <strong>automatic "
              "analyses that are not 100% accurate</strong> and <strong>do not "
              "constitute financial advice</strong>: always check every investment "
              "yourself and never rely blindly on the bot. Investing puts your capital "
              "at risk. Payments are handled by <strong>Stripe</strong>.",
    },
    "testimonials": {"it": "⭐ Cosa dicono i clienti", "en": "⭐ What our clients say"},
    "have_code": {"it": "Hai già un codice?", "en": "Already have a code?"},
    "activate_here": {"it": "Attiva qui →", "en": "Activate here →"},

    # --- pagina attivazione ---
    "activate_title": {"it": "Attiva il tuo accesso", "en": "Activate your access"},
    "activate_lead": {
        "it": "Inserisci il codice di attivazione che hai ricevuto via email dopo il pagamento.",
        "en": "Enter the activation code you received by email after payment.",
    },
    "activate_ph": {"it": "Codice di attivazione", "en": "Activation code"},
    "activate_btn": {"it": "Attiva e accedi", "en": "Activate and enter"},
    "back_to_plans": {"it": "← Torna ai piani", "en": "← Back to plans"},
}


def t(lang: str, key: str) -> str:
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("it") or key
