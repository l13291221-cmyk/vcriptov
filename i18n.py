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

    # --- impostazioni ---
    "set_title": {"it": "Impostazioni", "en": "Settings"},
    "set_sub": {"it": "Configura account, exchange, notifiche e strategia — tutto da qui, nessun file da modificare.",
                "en": "Set up account, exchange, notifications and strategy — all here, no files to edit."},
    "set_account": {"it": "Account", "en": "Account"},
    "set_active_plan": {"it": "Piano attivo", "en": "Active plan"},
    "set_exchange": {"it": "Exchange (collega il tuo conto)", "en": "Exchange (connect your account)"},
    "set_keys_enc": {"it": "Le chiavi vengono cifrate (AES) prima di essere salvate nel database. Non vengono mai mostrate in chiaro.",
                     "en": "Keys are encrypted (AES) before being saved in the database. They are never shown in clear text."},
    "set_kraken_warn": {
        "it": "🔒 <strong>Importante per la tua sicurezza:</strong> crea la chiave API su "
              "Kraken <strong>SENZA il permesso di prelievo (\"Withdraw funds\")</strong>. "
              "Dai solo i permessi di lettura e (se vuoi il trading automatico) di "
              "creazione ordini. Così, anche nel caso peggiore, nessuno potrà mai "
              "prelevare i tuoi fondi.",
        "en": "🔒 <strong>Important for your safety:</strong> create the API key on Kraken "
              "<strong>WITHOUT the withdrawal permission (\"Withdraw funds\")</strong>. "
              "Grant only read and (if you want automatic trading) order-creation "
              "permissions. That way, even in the worst case, no one can ever withdraw "
              "your funds.",
    },
    "set_enter_apikey": {"it": "Inserisci la tua API Key", "en": "Enter your API Key"},
    "set_enter_secret": {"it": "Inserisci il tuo Secret", "en": "Enter your Secret"},
    "set_current": {"it": "Attuale", "en": "Current"},
    "set_leave_blank": {"it": "lascia vuoto per non modificare.", "en": "leave blank to keep it."},
    "set_saved_blank": {"it": "Salvato ✓ — lascia vuoto per non modificare.", "en": "Saved ✓ — leave blank to keep it."},
    "set_tg_title": {"it": "Notifiche Telegram", "en": "Telegram notifications"},
    "set_tg_guide": {"it": "❓ Non sai come si fa? Apri la guida passo-passo",
                     "en": "❓ Don't know how? Open the step-by-step guide"},
    "set_tg_s1": {"it": "Apri Telegram e nella barra di ricerca in alto scrivi <b>@BotFather</b>. Apri quello con la spunta blu.",
                  "en": "Open Telegram and in the top search bar type <b>@BotFather</b>. Open the one with the blue checkmark."},
    "set_tg_s2": {"it": "Premi <b>Avvia</b> (o scrivi <code>/start</code>), poi scrivi <code>/newbot</code> e premi invio.",
                  "en": "Press <b>Start</b> (or type <code>/start</code>), then type <code>/newbot</code> and press enter."},
    "set_tg_s3": {"it": "BotFather ti chiede un <b>nome</b> (quello che vuoi) e poi uno <b>username</b> che deve finire con <code>bot</code> (es. <code>miosegnali_bot</code>).",
                  "en": "BotFather asks for a <b>name</b> (anything you like) and then a <b>username</b> that must end with <code>bot</code> (e.g. <code>mysignals_bot</code>)."},
    "set_tg_s4": {"it": "BotFather ti risponde con un <b>Token</b>, una riga tipo <code>123456789:AAE...xYz</code>. <b>Copialo e incollalo</b> nel campo “Token bot Telegram” qui sotto.",
                  "en": "BotFather replies with a <b>Token</b>, a line like <code>123456789:AAE...xYz</code>. <b>Copy and paste it</b> into the \"Telegram bot Token\" field below."},
    "set_tg_s5": {"it": "Ora serve il tuo <b>Chat ID</b>. Cerca <b>@userinfobot</b> su Telegram, aprilo e premi <b>Avvia</b>: ti risponde con un numero (“Id: 123456789”). <b>Copia quel numero</b> nel campo “Chat ID”.",
                  "en": "Now you need your <b>Chat ID</b>. Search <b>@userinfobot</b> on Telegram, open it and press <b>Start</b>: it replies with a number (\"Id: 123456789\"). <b>Copy that number</b> into the \"Chat ID\" field."},
    "set_tg_s6": {"it": "Cerca il <b>tuo</b> bot (l'username che hai scelto al punto 3) e premi <b>Avvia</b> almeno una volta, altrimenti non può scriverti.",
                  "en": "Search for <b>your</b> bot (the username you chose in step 3) and press <b>Start</b> at least once, otherwise it can't message you."},
    "set_tg_s7": {"it": "Premi <b>💾 Salva impostazioni</b> in fondo, poi torna qui e premi <b>“Invia messaggio di prova”</b>. Se ti arriva il messaggio, è tutto collegato! 🎉",
                  "en": "Press <b>💾 Save settings</b> at the bottom, then come back and press <b>\"Send a test message\"</b>. If the message arrives, everything is connected! 🎉"},
    "set_tg_token": {"it": "Token bot Telegram", "en": "Telegram bot Token"},
    "set_tg_token_hint": {"it": "Il codice che ti dà @BotFather (punto 4).", "en": "The code @BotFather gives you (step 4)."},
    "set_tg_chatid_hint": {"it": "Il numero che ti dà @userinfobot (punto 5).", "en": "The number @userinfobot gives you (step 5)."},
    "set_tg_test": {"it": "📨 Invia messaggio di prova", "en": "📨 Send a test message"},
    "set_tg_test_hint": {"it": "Salva prima le impostazioni, poi prova. Il messaggio di prova usa Token e Chat ID già salvati.",
                         "en": "Save the settings first, then test. The test message uses the already saved Token and Chat ID."},
    "set_tg_locked": {"it": "Disponibile nei piani Pro, VIP e Lifetime. Aggiorna il piano per abilitare le notifiche.",
                      "en": "Available on the Pro, VIP and Lifetime plans. Upgrade your plan to enable notifications."},
    "set_strategy": {"it": "🎯 Strategia", "en": "🎯 Strategy"},
    "set_strategy_hint": {"it": "Scegli quanto vuoi essere prudente o aggressivo. Imposta in automatico rischio, stop loss e take profit.",
                          "en": "Choose how cautious or aggressive you want to be. It sets risk, stop loss and take profit automatically."},
    "set_coins": {"it": "🪙 Crypto da seguire", "en": "🪙 Cryptos to follow"},
    "set_coins_hint": {"it": "Ricevi i segnali solo per le crypto che scegli. Se non ne selezioni nessuna, le ricevi tutte.",
                       "en": "Get signals only for the cryptos you choose. If you select none, you get them all."},
    "set_real": {"it": "⚠️ Trading REALE su Kraken (soldi veri)", "en": "⚠️ REAL trading on Kraken (real money)"},
    "set_real_hint": {
        "it": "Se acceso, quando tocchi <b>✅ Investi</b> sul messaggio Telegram il bot "
              "piazza un ordine <b>vero</b> sul tuo conto Kraken (con lo stop loss e take "
              "profit della strategia scelta). Servono API Key/Secret Kraken <b>con "
              "permesso di trading</b>. <b>Si rischiano soldi veri.</b> Inizia piccolo.",
        "en": "If enabled, when you tap <b>✅ Invest</b> on the Telegram message the bot "
              "places a <b>real</b> order on your Kraken account (with the stop loss and "
              "take profit of the chosen strategy). You need Kraken API Key/Secret <b>with "
              "trading permission</b>. <b>Real money is at risk.</b> Start small.",
    },
    "set_notify_only": {"it": "🔔 Solo notifiche (zero rischio, nessun ordine reale)",
                        "en": "🔔 Notifications only (zero risk, no real orders)"},
    "set_notify_only_hint": {"it": "Consigliato all'inizio: ricevi i segnali ma il bot NON esegue mai ordini con soldi veri, anche se il trading reale è acceso.",
                             "en": "Recommended at first: you get the signals but the bot NEVER places real-money orders, even if real trading is on."},
    "set_real_toggle": {"it": "Attiva il trading reale (parte SPENTO)", "en": "Enable real trading (starts OFF)"},
    "set_max_order": {"it": "Importo massimo per ordine (€)", "en": "Maximum amount per order (€)"},
    "set_max_order_hint": {"it": "Tetto di spesa per ogni singolo investimento.", "en": "Spending cap for each individual investment."},
    "set_advanced": {"it": "🔧 Personalizzazione avanzata (VIP)", "en": "🔧 Advanced customization (VIP)"},
    "set_advanced_hint": {"it": "Facoltativo: affina i parametri oltre alla strategia scelta sopra. Sovrascrive i valori della strategia.",
                          "en": "Optional: fine-tune the parameters beyond the strategy above. It overrides the strategy values."},
    "set_risk_trade": {"it": "Rischio per operazione (%)", "en": "Risk per trade (%)"},
    "set_fast_ma": {"it": "Media mobile veloce (periodi)", "en": "Fast moving average (periods)"},
    "set_slow_ma": {"it": "Media mobile lenta (periodi)", "en": "Slow moving average (periods)"},
    "set_sl": {"it": "Stop loss (%)", "en": "Stop loss (%)"},
    "set_tp": {"it": "Take profit (%)", "en": "Take profit (%)"},
    "set_engine_on": {"it": "Motore di trading attivo", "en": "Trading engine active"},
    "set_engine_hint": {"it": "Se disattivato, il bot smette di aprire nuove posizioni per il tuo account.",
                        "en": "If disabled, the bot stops opening new positions for your account."},
    "set_save": {"it": "💾 Salva impostazioni", "en": "💾 Save settings"},
    "set_subscription": {"it": "💳 Abbonamento", "en": "💳 Subscription"},
    "set_lifetime": {"it": "Hai il piano <b>Lifetime</b>: pagamento unico, nessun rinnovo. L'accesso non scade.",
                     "en": "You have the <b>Lifetime</b> plan: one-time payment, no renewal. Access never expires."},
    "set_renews_1": {"it": "Il tuo abbonamento si <b>rinnova automaticamente</b>",
                     "en": "Your subscription <b>renews automatically</b>"},
    "set_next_renew": {"it": "prossimo rinnovo intorno al", "en": "next renewal around"},
    "set_renews_2": {"it": "Puoi disdire quando vuoi: <b>mantieni l'accesso fino alla scadenza</b> già pagata e poi non ti verrà più addebitato nulla.",
                     "en": "You can cancel anytime: <b>you keep access until the end</b> of the period already paid, and then nothing more is charged."},
    "set_cancel_btn": {"it": "Disdici il rinnovo automatico", "en": "Cancel auto-renewal"},
    "set_cancel_confirm": {"it": "Vuoi davvero disdire il rinnovo automatico? Manterrai l&#39;accesso fino alla scadenza.",
                           "en": "Do you really want to cancel auto-renewal? You'll keep access until expiry."},
    "set_no_sub": {"it": "Su questo account non risulta un rinnovo automatico attivo (es. accesso demo o codice).",
                   "en": "This account has no active auto-renewal (e.g. demo or code access)."},
    "test_sending": {"it": "Invio in corso…", "en": "Sending…"},
    "test_sent": {"it": "✅ Inviato! Controlla Telegram.", "en": "✅ Sent! Check Telegram."},
    "test_neterr": {"it": "❌ Errore di rete", "en": "❌ Network error"},

    # --- come funziona ---
    "hiw_title": {"it": "Come funziona VCriptoV", "en": "How VCriptoV works"},
    "hiw_sub": {"it": "Semplice, in 3 passaggi", "en": "Simple, in 3 steps"},
    "hiw_s1_t": {"it": "Scegli un piano", "en": "Choose a plan"},
    "hiw_s1_p": {"it": "Attiva un abbonamento (o la prova gratuita). Ricevi subito un codice di attivazione, anche via email, per entrare nella dashboard.",
                 "en": "Start a subscription (or the free trial). You instantly get an activation code, also by email, to enter the dashboard."},
    "hiw_s2_t": {"it": "Collega Telegram e Kraken", "en": "Connect Telegram and Kraken"},
    "hiw_s2_p": {"it": "Dalle Impostazioni colleghi il tuo Telegram e il tuo conto Kraken. Bastano pochi minuti, con la guida passo-passo integrata.",
                 "en": "From Settings you connect your Telegram and your Kraken account. It takes a few minutes, with the built-in step-by-step guide."},
    "hiw_s3_t": {"it": "Ricevi i segnali", "en": "Receive the signals"},
    "hiw_s3_p": {"it": "Il bot analizza il mercato reale e ti manda i segnali su Telegram (“COMPRA X, stop loss, take profit”) con i tasti Investi / Non investire.",
                 "en": "The bot analyzes the real market and sends you signals on Telegram (\"BUY X, stop loss, take profit\") with Invest / Don't invest buttons."},
    "hiw_faq": {"it": "Domande frequenti", "en": "Frequently asked questions"},
    "hiw_q1": {"it": "Il bot guadagna sicuro?", "en": "Does the bot guarantee profits?"},
    "hiw_a1": {"it": "No. I segnali sono analisi automatiche <b>non accurate al 100%</b> e non sono consulenza finanziaria. Il trading di criptovalute è rischioso: puoi perdere il capitale. Valuta sempre tu ogni operazione.",
               "en": "No. The signals are automatic analyses that are <b>not 100% accurate</b> and are not financial advice. Crypto trading is risky: you can lose your capital. Always assess every trade yourself."},
    "hiw_q2": {"it": "Devo saper programmare o essere esperto?", "en": "Do I need to code or be an expert?"},
    "hiw_a2": {"it": "No. È tutto guidato: scegli il piano, colleghi Telegram e Kraken, e ricevi i segnali. Se hai dubbi c'è l'assistenza.",
               "en": "No. Everything is guided: choose a plan, connect Telegram and Kraken, and receive signals. If in doubt, support is there."},
    "hiw_q3": {"it": "I miei soldi passano da voi?", "en": "Does my money go through you?"},
    "hiw_a3": {"it": "No. Colleghi il <b>tuo</b> conto Kraken: gli ordini restano sul tuo conto. Noi non deteniamo i tuoi fondi.",
               "en": "No. You connect <b>your</b> Kraken account: orders stay on your account. We never hold your funds."},
    "hiw_q4": {"it": "Posso disdire quando voglio?", "en": "Can I cancel anytime?"},
    "hiw_a4": {"it": "Sì. Puoi disdire il rinnovo automatico dalle Impostazioni: mantieni l'accesso fino alla scadenza già pagata, senza vincoli.",
               "en": "Yes. You can cancel auto-renewal from Settings: you keep access until the period already paid, with no strings attached."},
    "hiw_q5": {"it": "Come funziona la prova gratuita?", "en": "How does the free trial work?"},
    "hiw_a5": {"it": "Provi tutte le funzioni per 3 giorni senza pagare. Alla fine, se ti trovi bene, scegli un piano per continuare.",
               "en": "You try all features for 3 days without paying. At the end, if you like it, choose a plan to continue."},
    "hiw_back": {"it": "← Torna agli abbonamenti", "en": "← Back to plans"},

    # --- scelta influencer ---
    "ci_last": {"it": "Ultima cosa!", "en": "One last thing!"},
    "ci_lead": {"it": "Da quale influencer hai conosciuto VCriptoV? Aiutaci a capire da dove arrivi.",
                "en": "Which influencer told you about VCriptoV? Help us understand where you came from."},
    "ci_enter": {"it": "Entra nella dashboard →", "en": "Enter the dashboard →"},

    # --- scaduto ---
    "exp_title": {"it": "Abbonamento scaduto", "en": "Subscription expired"},
    "exp_lead_1": {"it": "Il tuo abbonamento", "en": "Your"},
    "exp_lead_2": {"it": "è scaduto, quindi l'accesso alla dashboard è bloccato. Per continuare a usare il bot, rinnova scegliendo di nuovo un piano.",
                   "en": "subscription has expired, so dashboard access is blocked. To keep using the bot, renew by choosing a plan again."},
    "exp_renew": {"it": "Rinnova l'abbonamento →", "en": "Renew subscription →"},
    "exp_help": {"it": "Se pensi sia un errore (hai già pagato il rinnovo), contatta l'assistenza:",
                 "en": "If you think this is a mistake (you already paid the renewal), contact support:"},

    # --- termini ---
    "terms_title": {"it": "Prima di continuare — leggi e accetta", "en": "Before you continue — read and accept"},
    "terms_1": {"it": "<b>1. Nessuna garanzia sui risultati.</b> VCriptoV è uno strumento di analisi automatica. I segnali e le analisi <b>non sono accurati al 100%</b> e <b>non garantiscono alcun profitto</b>. Le performance passate non sono indicative di risultati futuri.",
                "en": "<b>1. No guarantee of results.</b> VCriptoV is an automatic analysis tool. Signals and analyses are <b>not 100% accurate</b> and <b>do not guarantee any profit</b>. Past performance is not indicative of future results."},
    "terms_2": {"it": "<b>2. Non è consulenza finanziaria.</b> Nulla di ciò che trovi qui costituisce consulenza finanziaria, di investimento, fiscale o legale. Le decisioni di investimento sono esclusivamente tue.",
                "en": "<b>2. Not financial advice.</b> Nothing here constitutes financial, investment, tax or legal advice. Investment decisions are entirely your own."},
    "terms_3": {"it": "<b>3. Rischio elevato.</b> Il trading di criptovalute è altamente rischioso e volatile: <b>puoi perdere tutto il capitale investito</b>. Investi solo denaro che puoi permetterti di perdere.",
                "en": "<b>3. High risk.</b> Crypto trading is highly risky and volatile: <b>you can lose all your invested capital</b>. Only invest money you can afford to lose."},
    "terms_4": {"it": "<b>4. Nessuna responsabilità per le perdite.</b> Usando il servizio accetti che <b>VCriptoV e il suo titolare NON sono responsabili</b> di eventuali perdite, danni o mancati guadagni derivanti dall'uso del bot, dei segnali o dell'esecuzione automatica degli ordini sul tuo exchange. Sei tu l'unico responsabile delle tue operazioni e del tuo conto.",
                "en": "<b>4. No liability for losses.</b> By using the service you accept that <b>VCriptoV and its owner are NOT liable</b> for any losses, damages or missed gains arising from use of the bot, the signals or the automatic execution of orders on your exchange. You are solely responsible for your trades and your account."},
    "terms_5": {"it": "<b>5. Verifica sempre.</b> Controlla personalmente ogni operazione prima di confermarla e non affidarti ciecamente al bot.",
                "en": "<b>5. Always verify.</b> Check every trade yourself before confirming it and never rely blindly on the bot."},
    "terms_6": {"it": "<b>6. Requisiti.</b> Dichiari di essere maggiorenne e di poter operare legalmente con le criptovalute nel tuo Paese.",
                "en": "<b>6. Requirements.</b> You declare that you are of legal age and may legally trade cryptocurrencies in your country."},
    "terms_7": {"it": "<b>7. Chiavi e dati.</b> Le chiavi API dell'exchange e i dati che inserisci restano sotto la tua responsabilità; vengono conservati in forma cifrata per il funzionamento del servizio.",
                "en": "<b>7. Keys and data.</b> Your exchange API keys and the data you enter remain your responsibility; they are stored encrypted to run the service."},
    "terms_8": {"it": "<b>8. Cookie.</b> Questo sito usa <b>cookie tecnici</b> necessari all'accesso e al mantenimento della sessione. Continuando, ne accetti l'uso.",
                "en": "<b>8. Cookies.</b> This site uses <b>technical cookies</b> needed for login and to keep your session. By continuing, you accept their use."},
    "terms_foot": {"it": "Premendo “Accetto” dichiari di aver letto, compreso e accettato integralmente quanto sopra.",
                   "en": "By pressing \"I accept\" you declare that you have read, understood and fully accepted the above."},
    "terms_accept": {"it": "✅ Accetto e continuo", "en": "✅ I accept and continue"},

    # --- checkout / codice generato ---
    "co_title_demo": {"it": "Codice demo generato", "en": "Demo code generated"},
    "co_title_ok": {"it": "Pagamento confermato", "en": "Payment confirmed"},
    "co_trial": {"it": "🎁 <strong>Prova gratuita di 3 giorni attivata!</strong> Accesso completo senza pagamento. Alla scadenza, scegli un piano per continuare.",
                 "en": "🎁 <strong>3-day free trial activated!</strong> Full access with no payment. When it ends, choose a plan to continue."},
    "co_demo": {"it": "🧪 <strong>Modalità DEMO:</strong> nessun pagamento reale è stato effettuato. Codice generato per provare il sito.",
                "en": "🧪 <strong>DEMO mode:</strong> no real payment was made. Code generated to try the site."},
    "co_activated_1": {"it": "Piano", "en": "Plan"},
    "co_activated_2": {"it": "attivato per", "en": "activated for"},
    "co_activated_3": {"it": ". Ecco il tuo codice di attivazione (lo abbiamo anche \"inviato\" alla tua email):",
                       "en": ". Here is your activation code (we also \"sent\" it to your email):"},
    "co_copy": {"it": "📋 Copia codice", "en": "📋 Copy code"},
    "co_copied": {"it": "✓ Copiato!", "en": "✓ Copied!"},
    "co_enter": {"it": "Inserisci il codice e accedi →", "en": "Enter the code and log in →"},
    "co_keep": {"it": "Conserva questo codice: è legato al tuo piano e alla tua email. Serve per sbloccare la dashboard.",
                "en": "Keep this code: it's tied to your plan and email. You need it to unlock the dashboard."},
}


def t(lang: str, key: str) -> str:
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("it") or key
