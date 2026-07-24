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
    "back_to_site": {"it": "← Torna al sito", "en": "← Back to the site"},

    # --- dashboard ---
    "dash_title": {"it": "Dashboard di trading", "en": "Trading dashboard"},
    "dash_plan": {"it": "Piano", "en": "Plan"},
    "dash_monitored": {"it": "crypto monitorate", "en": "cryptos monitored"},
    "dash_botactive": {"it": "Bot attivo · aggiornamento ogni 30s",
                       "en": "Bot active · updates every 30s"},
    "dash_data": {"it": "dati…", "en": "data…"},
    "dash_sentiment_on": {"it": "Filtro sentiment ON", "en": "Sentiment filter ON"},
    "dash_risk": {
        "it": "⚠️ <b>Avviso.</b> I segnali del bot sono analisi automatiche e <b>non "
              "sono accurati al 100%</b>. Non costituiscono consulenza finanziaria: "
              "<b>controlla sempre tu ogni investimento</b> e non affidarti ciecamente "
              "al bot. Investendo rischi il tuo capitale.",
        "en": "⚠️ <b>Warning.</b> The bot's signals are automatic analyses and are "
              "<b>not 100% accurate</b>. They are not financial advice: <b>always check "
              "every investment yourself</b> and never rely blindly on the bot. "
              "Investing puts your capital at risk.",
    },
    "dash_connect": {
        "it": "🔗 <b>Collega il tuo Kraken</b> nelle Impostazioni per vedere qui i tuoi "
              "dati reali: saldo, operazioni e profitti. Finché non è collegato, non "
              "mostriamo numeri inventati.",
        "en": "🔗 <b>Connect your Kraken</b> in Settings to see your real data here: "
              "balance, trades and profits. Until it's connected, we don't show made-up "
              "numbers.",
    },
    "kpi_equity": {"it": "Equity totale", "en": "Total equity"},
    "kpi_pnl": {"it": "P&L totale", "en": "Total P&L"},
    "kpi_cash": {"it": "Liquidità", "en": "Cash"},
    "kpi_invested": {"it": "Investito", "en": "Invested"},
    "kpi_open": {"it": "Posizioni aperte", "en": "Open positions"},
    "kpi_winrate": {"it": "Win rate", "en": "Win rate"},
    "kpi_connect_kraken": {"it": "Collega Kraken", "en": "Connect Kraken"},
    "panel_account_trend": {"it": "Andamento del conto", "en": "Account performance"},
    "chart_connect": {"it": "Collega il tuo Kraken per vedere l'andamento reale del conto.",
                      "en": "Connect your Kraken to see your real account performance."},
    "panel_prices": {"it": "Prezzi di mercato", "en": "Market prices"},
    "loading": {"it": "Caricamento…", "en": "Loading…"},
    "panel_positions": {"it": "Posizioni aperte", "en": "Open positions"},
    "panel_history": {"it": "Storico operazioni", "en": "Trade history"},
    "th_crypto": {"it": "Crypto", "en": "Crypto"},
    "th_side": {"it": "Lato", "en": "Side"},
    "th_qty": {"it": "Quantità", "en": "Quantity"},
    "th_entry": {"it": "Prezzo entrata", "en": "Entry price"},
    "th_current": {"it": "Prezzo attuale", "en": "Current price"},
    "th_in": {"it": "Entrata", "en": "In"},
    "th_out": {"it": "Uscita", "en": "Out"},
    "th_closed": {"it": "Chiusa", "en": "Closed"},
    "th_action": {"it": "Azione", "en": "Action"},
    "th_price": {"it": "Prezzo", "en": "Price"},
    "th_result": {"it": "Esito", "en": "Result"},
    "th_when": {"it": "Quando", "en": "When"},
    "no_open_pos": {"it": "Nessuna posizione aperta", "en": "No open positions"},
    "no_closed_trades": {"it": "Nessuna operazione chiusa", "en": "No closed trades"},
    "panel_kraken": {"it": "💰 Conto Kraken reale", "en": "💰 Real Kraken account"},
    "not_connected": {"it": "non collegato", "en": "not connected"},
    "kraken_hint": {
        "it": "Collega Kraken e attiva il trading reale nelle Impostazioni per vedere "
              "qui saldo e operazioni vere.",
        "en": "Connect Kraken and enable real trading in Settings to see your real "
              "balance and trades here.",
    },
    "panel_alerts": {"it": "🔔 Avvisi di prezzo", "en": "🔔 Price alerts"},
    "alerts_hint": {"it": "Ti avvisiamo su Telegram quando una crypto raggiunge il prezzo che scegli.",
                    "en": "We'll alert you on Telegram when a crypto reaches the price you choose."},
    "alert_below": {"it": "scende sotto", "en": "drops below"},
    "alert_above": {"it": "sale sopra", "en": "rises above"},
    "alert_price_ph": {"it": "Prezzo ($)", "en": "Price ($)"},
    "alert_add": {"it": "+ Aggiungi", "en": "+ Add"},
    "panel_signals": {"it": "📨 Segnali inviati su Telegram", "en": "📨 Signals sent on Telegram"},
    "signals_hint": {
        "it": "I segnali sono indicativi e non accurati al 100%: valuta sempre tu prima di investire.",
        "en": "Signals are indicative and not 100% accurate: always decide for yourself before investing.",
    },
    "no_signals": {"it": "Nessun segnale ancora", "en": "No signals yet"},

    # --- classifica ---
    "lb_title": {"it": "🏆 Classifica utenti", "en": "🏆 User leaderboard"},
    "lb_sub": {"it": "I 10 utenti che hanno guadagnato di più con i segnali del bot",
               "en": "The 10 users who earned the most with the bot's signals"},
    "lb_anon": {
        "it": "🔒 <b>Tutto anonimo.</b> Non mostriamo mai nomi, email o dati personali "
              "di nessuno. I guadagni sono <b>stime basate sui segnali</b> del bot (a "
              "target / stop), non profitti garantiti: i risultati passati non "
              "assicurano quelli futuri.",
        "en": "🔒 <b>Fully anonymous.</b> We never show anyone's name, email or personal "
              "data. Earnings are <b>estimates based on the bot's signals</b> (target / "
              "stop), not guaranteed profits: past results don't ensure future ones.",
    },
    "lb_user": {"it": "Utente", "en": "User"},
    "lb_gain": {"it": "Guadagno stimato", "en": "Estimated earnings"},
    "lb_withcoin": {"it": "Con quale cripto", "en": "With which crypto"},
    "lb_method": {"it": "Metodo (rischio)", "en": "Method (risk)"},
    "lb_empty": {"it": "Ancora nessun guadagno da mostrare: la classifica si riempirà man mano che i segnali del bot vengono chiusi.",
                 "en": "No earnings to show yet: the leaderboard fills up as the bot's signals get closed."},
    "risk_low": {"it": "Rischio basso", "en": "Low risk"},
    "risk_medium": {"it": "Rischio medio", "en": "Medium risk"},
    "risk_high": {"it": "Rischio alto", "en": "High risk"},
}


def t(lang: str, key: str) -> str:
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("it") or key
