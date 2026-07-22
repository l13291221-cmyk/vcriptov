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
if [ ! -s instance/stripe.key ]; then
  echo ""
  echo "----------------------------------------------"
  echo "Incolla la tua STRIPE SECRET KEY e premi Invio."
  echo "(inizia con sk_live_...  per soldi veri, oppure sk_test_...  per le prove)"
  echo "----------------------------------------------"
  read -r STRIPE_KEY
  if [ -z "$STRIPE_KEY" ]; then
    echo "Nessuna chiave inserita. Riesegui il file quando ce l'hai."
    exit 1
  fi
  printf '%s' "$STRIPE_KEY" > instance/stripe.key
  echo "-> Chiave salvata. Non te la chiederò più."
fi

# --- 3. Avvio ----------------------------------------------------------
echo ""
echo "=============================================="
echo "  Sito avviato! Apri il browser su:"
echo "     http://127.0.0.1:5001"
echo "  (per fermarlo: premi Ctrl+C in questa finestra)"
echo "=============================================="
python app.py
