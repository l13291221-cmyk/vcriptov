#!/usr/bin/env bash
# Aggiorna VCriptoV all'ultima versione (Mac/Linux), senza riscaricare.
# Funziona se hai scaricato il progetto con "git clone".
cd "$(dirname "$0")"

if ! command -v git >/dev/null 2>&1; then
  echo "Git non è installato. Installalo e riprova."
  exit 1
fi
if [ ! -d ".git" ]; then
  echo "Questa cartella non è un 'git clone'. Vedi README, sezione Aggiornamenti."
  exit 1
fi

echo "Scarico gli aggiornamenti..."
git pull
echo "Aggiornamento completato. Riavvia con: bash start.sh"
