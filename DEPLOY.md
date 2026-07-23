# Pubblicare VCriptoV online (server sempre acceso)

Questa guida ti fa mettere il sito online con un **link vero** che i clienti
possono aprire da telefono o computer, 24 ore su 24.

> Nel frattempo puoi **continuare a usarlo sul tuo computer** con `start.bat`:
> la pubblicazione non cambia nulla dell'uso locale.

Consigliato: **Render** (semplice). In alternativa Railway o un VPS.

---

## Cosa serve (una volta sola)
1. Il progetto su **GitHub** (già fatto: è nel tuo repository).
2. Un account su **[render.com](https://render.com)** (con la tua email).
3. La tua **Stripe Secret Key** vera (`sk_live_...` per incassare davvero).

---

## Passo per passo su Render

1. Vai su **render.com** e registrati / accedi.
2. In alto premi **New +** → **Web Service**.
3. Collega il tuo **GitHub** e scegli il repository di VCriptoV.
4. Render legge da solo il file `render.yaml`. Se te lo chiede, conferma:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT`
   - ⚠️ Lascia **1 worker** (importante: così il bot in background gira una volta sola).
5. **Disco persistente** (per non perdere i dati ad ogni aggiornamento):
   aggiungi un **Disk** con *Mount Path* = `/var/data` e 1 GB.
   Poi imposta la variabile d'ambiente **`INSTANCE_DIR` = `/var/data`**.
   *(Il disco richiede un piano Render a pagamento — pochi $ al mese.)*
6. **Variabili d'ambiente** (sezione *Environment*):
   - `INSTANCE_DIR` = `/var/data`
   - `STRIPE_SECRET_KEY` = la tua chiave `sk_live_...` (o `sk_test_...` per prove)
   - *(facoltativo)* `PYTHON_VERSION` = `3.12.10`
7. Premi **Create Web Service**. Render installa e avvia: in qualche minuto ti dà
   un link tipo `https://vcriptov.onrender.com`. **Quello è il tuo sito online.** 🎉

---

## Dopo la pubblicazione
- Apri il link, entra in **Area creatore**, e da lì configuri tutto come in locale.
- I dati (licenze, impostazioni, chiavi Kraken dei clienti) restano salvati sul
  disco persistente, anche quando aggiorni il sito.
- Per aggiornare il sito in futuro: basta fare **push su GitHub**, Render
  ri-pubblica da solo.

## Rinnovi automatici degli abbonamenti (webhook Stripe)
Gli abbonamenti mensili scadono dopo 30 giorni. Perché il rinnovo di chi
continua a pagare estenda l'accesso **da solo**, va collegato un webhook Stripe:
1. Su Stripe: **Developers → Webhooks → Add endpoint**.
2. URL endpoint: `https://IL-TUO-SITO.onrender.com/stripe/webhook`
3. Eventi da inviare: `invoice.paid`, `invoice.payment_failed`,
   `customer.subscription.deleted`.
4. Stripe ti dà un **Signing secret** (`whsec_...`): mettilo su Render nella
   variabile `STRIPE_WEBHOOK_SECRET`.

Senza webhook, il blocco dopo 30 giorni funziona lo stesso, ma i rinnovi li
dovrai estendere a mano dall'Area creatore (pulsante **+30gg**).

## Note importanti
- **Database:** di default usa un file SQLite sul disco persistente (semplice, va
  bene per iniziare). Se un giorno avrai tanti clienti, potrai passare a un
  database Postgres impostando la variabile `DATABASE_URL` (il codice lo supporta
  già) — te lo spiego quando servirà.
- **Sicurezza chiavi:** la Stripe Secret Key sta solo nelle variabili d'ambiente
  di Render, mai nel codice.
- **Aspetti legali:** prima di incassare da clienti veri, ricorda la verifica
  con un avvocato/commercialista di cui abbiamo parlato.
