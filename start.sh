#!/usr/bin/env bash
# Spam Uitschrijver — startscript voor Mac / Linux

set -e
cd "$(dirname "$0")"

# Installeer dependencies als ze er nog niet zijn
if ! python3 -c "import flask" 2>/dev/null; then
  echo "Dependencies installeren..."
  pip3 install -r requirements.txt
fi

# Controleer of .env bestaat
if [ ! -f .env ]; then
  echo ""
  echo "⚠️  Geen .env bestand gevonden."
  echo "   Kopieer .env.example naar .env en vul je gegevens in."
  echo "   Zie de setup-pagina voor instructies."
  echo ""
  exit 1
fi

echo ""
echo "✅  Spam Uitschrijver wordt gestart..."
echo "    Open je Tailscale-adres in Safari op je iPhone."
echo "    Druk Ctrl+C om te stoppen."
echo ""

gunicorn app:app \
  --bind 127.0.0.1:5000 \
  --workers 1 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
