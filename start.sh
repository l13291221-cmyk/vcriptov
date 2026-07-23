#!/usr/bin/env bash
#
# Avviatore "tutto-in-uno" di VCriptoV per Mac / Linux.
# Doppio click (o:  bash start.sh) e fa tutto da solo:
#   1. prepara l'ambiente Python e installa le dipendenze;
#   2. la PRIMA volta ti chiede la tua Stripe Secret Key e la salva
#      in instance/stripe.key (file locale, mai caricato su GitHub);
#   3. avvia il sito su http://127.0.0.1:5001
#
set -e
cd "$(dirname "$0")"

echo "=============================================="
echo "   VCriptoV - avvio del sito"
echo "=============================================="

# --- 0. Aggiornamento automatico (se è un git clone) -------------------
if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
  echo "-> Controllo aggiornamenti..."
  git pull >/dev/null 2>&1 || true
fi

# --- 1. Python + ambiente virtuale -------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERRORE: Python 3 non è installato."
  echo "Scaricalo da https://www.python.org/downloads/ e riesegui questo file."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "-> Preparo l'ambiente (solo la prima volta, può richiedere 1-2 minuti)..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "-> Installo/aggiorno le dipendenze..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

# --- 2. Stripe Secret Key (chiesta una sola volta) ---------------------
mkdir -p instance
# Scelta modalità: demo o reale (solo se non già configurata)
need_setup=1
if [ -s instance/stripe.key ]; then
  if grep -qi '^sk_' instance/stripe.key || grep -qi '^demo' instance/stripe.key; then
    need_setup=0
  fi
fi
if [ "$need_setup" = "1" ]; then
  echo ""
  echo "=============================================="
  echo "  Come vuoi avviare il sito?"
  echo "    demo   = per provarlo tu, senza pagamenti"
  echo "    reale  = i clienti pagano davvero (serve la chiave Stripe)"
  echo "=============================================="
  read -r MODE
  case "$(echo "$MODE" | tr '[:upper:]' '[:lower:]')" in
    demo)
      printf 'demo' > instance/stripe.key
      echo "-> Modalità DEMO attivata." ;;
    reale|real)
      echo "Incolla la tua STRIPE SECRET KEY (sk_live_... o sk_test_...) e premi Invio:"
      read -r STRIPE_KEY
      if [ -z "$STRIPE_KEY" ]; then echo "Nessuna chiave inserita."; exit 1; fi
      printf '%s' "$STRIPE_KEY" > instance/stripe.key
      echo "-> Modalità REALE attivata." ;;
    *)
      echo "Scrivi demo oppure reale. Riesegui il file."; exit 1 ;;
  esac
fi

# --- 3. Avvio ----------------------------------------------------------
echo ""
echo "=============================================="
echo "  Sito avviato! Apri il browser su:"
echo "     http://127.0.0.1:5001"
echo "  (per fermarlo: premi Ctrl+C in questa finestra)"
echo "=============================================="
python app.py
