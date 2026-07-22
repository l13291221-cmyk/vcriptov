# VCriptoV — Bot di Trading Crypto (Flask)

Applicazione web completa in **Python / Flask** per un bot di trading di
criptovalute con **paywall a piani di abbonamento**, **generazione automatica
del codice di attivazione (license key)**, **pagina Impostazioni grafica** e
**dashboard di trading con grafici** (Chart.js). Il motore di trading gira in
**background** e si aggiorna ogni 30 secondi.

> ⚠️ **Avviso importante.** Questo è un software **dimostrativo/didattico**.
> Il motore esegue **trading simulato (paper trading)** su prezzi generati
> internamente: **non invia ordini reali** ad alcun exchange e **non
> costituisce consulenza finanziaria**. Il flusso di pagamento è **simulato**.
> Prima di qualsiasi uso commerciale devi integrare un gateway di pagamento
> reale (Stripe/PayPal), collegare le API reali dell'exchange, e verificare i
> requisiti legali/regolamentari per la vendita di software finanziario nel
> tuo paese.

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
├── market.py           # Feed prezzi simulato (random walk) — punto di aggancio feed reale
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

## 🚀 Avvio passo dopo passo

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
| `BOT_INTERVAL_SECONDS` | `30` | Intervallo di aggiornamento del motore |
| `STARTING_EQUITY` | `10000` | Capitale virtuale iniziale per licenza |

Esempio (tick più veloce per fare test):
```bash
BOT_INTERVAL_SECONDS=5 python app.py
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
1. **Pagamenti reali:** sostituisci la sezione simulata in `app.py` (rotta
   `/checkout`) con una sessione Stripe/PayPal; genera la licenza solo dopo il
   webhook di pagamento riuscito.
2. **Trading reale:** in `market.py` collega il ticker reale dell'exchange e in
   `bot.py` sostituisci le operazioni simulate con ordini reali via API
   (usando le chiavi salvate dall'utente). Testa sempre prima in *sandbox*.
3. **Server WSGI:** esegui con `gunicorn` dietro reverse proxy (non usare il
   server di sviluppo Flask in produzione). Usa **un solo worker** o sposta il
   motore di trading in un processo/worker dedicato (es. Celery/APScheduler)
   per evitare più istanze del bot.
4. **Rinnovi/scadenze:** aggiungi la logica di scadenza per i piani mensili.
5. **Email:** collega un provider SMTP per inviare davvero il codice.
