# VCriptoV — Bot di Trading Crypto (Flask)

Applicazione web completa in **Python / Flask** per un bot di trading di
criptovalute con **paywall a piani di abbonamento**, **generazione automatica
del codice di attivazione (license key)**, **pagina Impostazioni grafica** e
**dashboard di trading con grafici** (Chart.js). Il motore di trading gira in
**background** e si aggiorna ogni 30 secondi.

> ⚠️ **Cosa è reale e cosa no (leggi bene).**
> - **Dati di mercato: REALI.** Il bot legge i prezzi veri da **Kraken** (via
>   `ccxt`) e calcola i segnali su dati reali. Nella dashboard un badge indica
>   se i dati sono `LIVE` o `offline`.
> - **Segnali su Telegram: REALI.** Ogni cliente collega il *proprio* bot
>   Telegram e riceve i segnali (apertura/chiusura) sul proprio account.
> - **Pagamenti: REALI**, tramite **Stripe** (vedi configurazione sotto).
> - **Esecuzione ordini con denaro vero: NON attiva.** Le operazioni mostrate
>   nella dashboard sono **simulate (paper trading) su prezzi reali**, a scopo di
>   track record: il bot **non compra/vende automaticamente** con i soldi del
>   cliente. È una scelta di sicurezza (un bug o una strategia errata
>   perderebbe denaro reale). Abilitare l'esecuzione reale è un passo separato e
>   va fatto con estrema cautela.
> - Nulla di questo **costituisce consulenza finanziaria**. Prima di vendere al
>   pubblico, verifica i requisiti legali/regolamentari del tuo paese.

> 🔑 **La chiave segreta Stripe NON è nel codice.** Incollala nel file locale
> `instance/stripe.key` (ignorato da git) — oppure usa la variabile d'ambiente
> `STRIPE_SECRET_KEY`. Vedi "Configurare Stripe" sotto. Non incollarla mai in un
> file tracciato da git: finirebbe nella cronologia del repository. Se una chiave
> `sk_live_...` viene esposta, revocala subito dal cruscotto Stripe
> (Developers → API keys → Roll key).

---

## ✨ Funzionalità

1. **Paywall obbligatorio** — alla prima apertura l'utente vede i 4 piani:
   - **Starter** (10€/mese) — segnali su BTC ed ETH.
   - **Pro** (25€/mese) — tutte le crypto, filtro sentiment, notifiche Telegram.
   - **VIP** (45€/mese, scontato da 60€) — Pro + strategia/rischio personalizzabili + segnali prioritari.
   - **Lifetime** (200€ una tantum) — tutte le funzioni VIP a vita.
2. **Codice di attivazione automatico** — dopo la scelta del piano viene
   generato un codice firmato (HMAC) legato a **email + piano**, salvato nel
   database e mostrato all'utente. È valido **solo** per quel livello di accesso.
3. **Impostazioni grafiche** (nessun `.env` da editare) — email, API key/secret
   dell'exchange e token Telegram si inseriscono da interfaccia web. Le
   credenziali sono **cifrate (AES/Fernet)** nel database.
4. **Dashboard di trading** — KPI (equity, P&L, liquidità, win rate), **curva di
   equity** (Chart.js), prezzi live, **posizioni aperte** e **storico operazioni**.

## 🗂️ Struttura del progetto

```
vcriptov/
├── app.py              # App Flask: rotte, paywall, attivazione, dashboard, API JSON
├── config.py           # Config + generazione automatica dei segreti (instance/)
├── plans.py            # Definizione piani, crypto supportate, prezzi iniziali
├── licensing.py        # Generazione/validazione codici di attivazione (HMAC)
├── security.py         # Cifratura Fernet delle credenziali utente
├── models.py           # Modelli DB (SQLAlchemy): License, Setting, Portfolio, Trade, EquityPoint
├── market.py           # Feed prezzi REALI da Kraken (ccxt), con fallback offline sicuro
├── bot.py              # Motore di trading in background (thread, tick ogni 30s)
├── notify.py           # Notifiche Telegram (best-effort)
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── paywall.html    # Schermata piani + email
│   ├── checkout.html   # Mostra il codice generato
│   ├── activate.html   # Inserimento codice
│   ├── dashboard.html  # Dashboard con grafici
│   ├── settings.html   # Pannello impostazioni
│   └── _sidebar.html
└── static/
    ├── css/style.css
    └── js/dashboard.js # Aggiornamento live via /api/*
```

Il database SQLite e i segreti generati automaticamente vengono creati nella
cartella `instance/` (ignorata da git).

## ⚡ Avvio facile (consigliato, un solo passaggio)

Non serve conoscere Python o la riga di comando. Nella cartella del progetto:

- **Windows:** fai **doppio click su `start.bat`**.
- **Mac / Linux:** fai doppio click su `start.sh` (oppure apri il Terminale nella
  cartella e scrivi `bash start.sh`).

Lo script fa tutto da solo: installa quello che serve, la **prima volta ti chiede
la tua Stripe Secret Key** (la incolli e premi Invio — viene salvata in
`instance/stripe.key`, un file che resta solo sul tuo computer), e poi apre il
sito. Quando vedi il messaggio, apri il browser su **http://127.0.0.1:5000**.

> Prerequisito unico: avere **Python 3** installato (https://www.python.org/downloads/;
> su Windows spunta *"Add Python to PATH"* durante l'installazione).

---

## 🚀 Avvio passo dopo passo (manuale)

### 1. Requisiti
- Python 3.10+ (testato su 3.11).

### 2. Clona / entra nella cartella
```bash
cd vcriptov
```

### 3. Crea e attiva un ambiente virtuale
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 4. Installa le dipendenze
```bash
pip install -r requirements.txt
```

### 5. Avvia l'applicazione
```bash
python app.py
```
Al primo avvio vengono creati automaticamente il database e le chiavi segrete
in `instance/`, e il motore di trading parte in background.

### 6. Apri il browser
```
http://127.0.0.1:5000
```

### 7. Prova il flusso completo
1. Nel **paywall** scegli un piano, inserisci l'email e premi *Procedi*.
2. Copia il **codice di attivazione** mostrato nella pagina di checkout.
3. Vai su *Inserisci il codice e accedi*, incolla il codice e **sblocca**.
4. Sei nella **dashboard**: entro ~1 minuto il bot inizia ad aprire posizioni
   simulate (servono alcuni tick per costruire le medie mobili) e i grafici si
   popolano.
5. Apri **Impostazioni** per inserire email, chiavi exchange, token Telegram e
   (piani VIP/Lifetime) i parametri di strategia.

## ⚙️ Configurazione opzionale (variabili d'ambiente)

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `STRIPE_SECRET_KEY` | *(nessuno)* | **Obbligatoria per i pagamenti.** Chiave segreta Stripe (`sk_live_...` in produzione, `sk_test_...` per i test) |
| `BOT_INTERVAL_SECONDS` | `30` | Intervallo di aggiornamento del motore |
| `STARTING_EQUITY` | `10000` | Capitale virtuale iniziale per licenza |

### Configurare Stripe (pagamenti reali)

1. Crea un account su [stripe.com](https://stripe.com) e recupera la tua chiave
   segreta da **Developers → API keys**.
2. **Modo consigliato — file locale (la scrivi una volta e basta):**
   crea il file `instance/stripe.key` e incolla dentro **solo** la chiave:
   ```bash
   echo "sk_live_LA_TUA_CHIAVE" > instance/stripe.key   # una sola riga, niente altro
   python app.py
   ```
   Questo file è **ignorato da git** (vedi `.gitignore`): la chiave resta sul tuo
   computer/server e **non finisce mai su GitHub**. Non serve alcuna variabile
   d'ambiente e l'avviso rosso "Pagamenti non configurati" sparisce.
3. **In alternativa** (utile su hosting come Render/Railway/Heroku) puoi usare la
   variabile d'ambiente, che ha la precedenza sul file:
   ```bash
   export STRIPE_SECRET_KEY="sk_live_..."     # Windows: set STRIPE_SECRET_KEY=sk_live_...
   ```
   Per i test usa la chiave `sk_test_...` e le [carte di test Stripe](https://docs.stripe.com/testing)
   (es. `4242 4242 4242 4242`).
4. Il flusso: l'utente sceglie il piano → viene reindirizzato al **Checkout
   ospitato da Stripe** → dopo il pagamento torna su `/checkout/success`, dove
   l'app **verifica l'esito con Stripe** e attiva la licenza mostrando il codice.

> ⚠️ **Non scrivere mai la chiave `sk_live_...` dentro `app.py`, `config.py` o
> qualsiasi file versionato:** finirebbe nella cronologia di git e su GitHub, che
> la revocherebbe automaticamente. Usa `instance/stripe.key` o la variabile
> d'ambiente. Se una `sk_live` viene esposta, revocala subito da Stripe
> (Developers → API keys → **Roll key**).

> Per maggiore robustezza in produzione conviene aggiungere anche un **webhook**
> Stripe (`checkout.session.completed`) come fonte di verità del pagamento,
> oltre al redirect di successo.

Esempio (tick più veloce per fare test, con chiave di test):
```bash
STRIPE_SECRET_KEY=sk_test_xxx BOT_INTERVAL_SECONDS=5 python app.py
```

## 🔐 Note sulla sicurezza
- Le credenziali exchange e il token Telegram sono cifrati con **Fernet**
  prima di essere salvati; nell'UI vengono mostrati solo **mascherati**.
- I codici licenza includono un **checksum HMAC**: non possono essere validati
  senza la chiave segreta del server.
- La chiave di sessione Flask, la chiave di firma licenze e la chiave di
  cifratura sono generate al primo avvio e conservate in `instance/` con
  permessi `0600`.

## 🧱 Passaggi per andare in produzione
1. **Pagamenti reali:** già integrati con **Stripe Checkout** (rotta
   `/checkout` + `/checkout/success`). Per la massima robustezza aggiungi un
   webhook `checkout.session.completed` come conferma definitiva del pagamento.
2. **Trading reale:** in `market.py` collega il ticker reale dell'exchange e in
   `bot.py` sostituisci le operazioni simulate con ordini reali via API
   (usando le chiavi salvate dall'utente). Testa sempre prima in *sandbox*.
3. **Server WSGI:** esegui con `gunicorn` dietro reverse proxy (non usare il
   server di sviluppo Flask in produzione). Usa **un solo worker** o sposta il
   motore di trading in un processo/worker dedicato (es. Celery/APScheduler)
   per evitare più istanze del bot.
4. **Rinnovi/scadenze:** aggiungi la logica di scadenza per i piani mensili.
5. **Email:** collega un provider SMTP per inviare davvero il codice.
