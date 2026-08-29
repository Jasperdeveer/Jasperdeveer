#!/usr/bin/env bash
# Automatisch Readarr + Prowlarr configureren via hun REST API's, zodat je dit
# niet handmatig in de webinterface hoeft te doen:
#  - root folder /books in Readarr
#  - Torbox als qBittorrent-compatibele downloadclient in Readarr
#  - Prowlarr <-> Readarr app-sync
#
# Wordt automatisch aangeroepen door install.sh nadat `docker compose up -d`
# is gedraaid. Losstaand opnieuw draaien kan ook: ./scripts/configure-apps.sh
set -uo pipefail

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$SETUP_DIR/.env" ] && set -a && source "$SETUP_DIR/.env" && set +a

READARR_URL="http://localhost:8787"
PROWLARR_URL="http://localhost:9696"

extract_api_key() {
  grep -oP '(?<=<ApiKey>)[^<]+' "$1" 2>/dev/null || true
}

echo "==> Wachten tot Readarr en Prowlarr hun config.xml genereren..."
for _ in $(seq 1 60); do
  READARR_API_KEY="$(extract_api_key "$SETUP_DIR/config/readarr/config.xml")"
  PROWLARR_API_KEY="$(extract_api_key "$SETUP_DIR/config/prowlarr/config.xml")"
  [ -n "$READARR_API_KEY" ] && [ -n "$PROWLARR_API_KEY" ] && break
  sleep 2
done

if [ -z "${READARR_API_KEY:-}" ] || [ -z "${PROWLARR_API_KEY:-}" ]; then
  echo "!! Kon geen API-keys vinden -- draai dit script later opnieuw met: ./scripts/configure-apps.sh"
  exit 1
fi

echo "==> Wachten tot de API's reageren..."
for _ in $(seq 1 60); do
  curl -sf -H "X-Api-Key: $READARR_API_KEY" "$READARR_URL/api/v1/system/status" >/dev/null 2>&1 && \
  curl -sf -H "X-Api-Key: $PROWLARR_API_KEY" "$PROWLARR_URL/api/v1/system/status" >/dev/null 2>&1 && break
  sleep 2
done

echo "==> Root folder /books toevoegen aan Readarr..."
curl -sf -X POST "$READARR_URL/api/v1/rootfolder" \
  -H "X-Api-Key: $READARR_API_KEY" -H "Content-Type: application/json" \
  -d '{"path":"/books","name":"Books"}' >/dev/null \
  && echo "  OK" || echo "  overgeslagen (bestond al, of API-vorm gewijzigd -- controleer handmatig)"

if [ -n "${TORBOX_API_KEY:-}" ]; then
  echo "==> Torbox toevoegen als downloadclient in Readarr..."
  curl -sf -X POST "$READARR_URL/api/v1/downloadclient" \
    -H "X-Api-Key: $READARR_API_KEY" -H "Content-Type: application/json" \
    -d "{
      \"enable\": true,
      \"protocol\": \"torrent\",
      \"priority\": 1,
      \"name\": \"Torbox\",
      \"implementation\": \"QBittorrent\",
      \"configContract\": \"QBittorrentSettings\",
      \"fields\": [
        {\"name\": \"host\", \"value\": \"qbittorrent.torbox.app\"},
        {\"name\": \"port\", \"value\": 443},
        {\"name\": \"useSsl\", \"value\": true},
        {\"name\": \"username\", \"value\": \"${TORBOX_API_KEY}\"},
        {\"name\": \"password\", \"value\": \"${TORBOX_API_KEY}\"},
        {\"name\": \"category\", \"value\": \"readarr\"}
      ]
    }" >/dev/null \
    && echo "  OK" || echo "  mislukt of bestond al -- controleer handmatig in Readarr (Settings > Download Clients). Torbox kan host/veldnamen wijzigen, check hun Integrations-pagina."
else
  echo "==> TORBOX_API_KEY niet gezet in .env -- downloadclient-configuratie overgeslagen."
  echo "    Vul .env aan en draai dit script opnieuw: ./scripts/configure-apps.sh"
fi

echo "==> Prowlarr koppelen aan Readarr (app-sync)..."
curl -sf -X POST "$PROWLARR_URL/api/v1/applications" \
  -H "X-Api-Key: $PROWLARR_API_KEY" -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Readarr\",
    \"implementation\": \"Readarr\",
    \"configContract\": \"ReadarrSettings\",
    \"syncLevel\": \"fullSync\",
    \"fields\": [
      {\"name\": \"prowlarrUrl\", \"value\": \"http://prowlarr:9696\"},
      {\"name\": \"baseUrl\", \"value\": \"http://readarr:8787\"},
      {\"name\": \"apiKey\", \"value\": \"${READARR_API_KEY}\"}
    ]
  }" >/dev/null \
  && echo "  OK" || echo "  mislukt of bestond al -- controleer handmatig in Prowlarr (Settings > Apps)"

cat <<EOF

==> Klaar (best-effort). Controleer resultaat in de webinterfaces:
    Readarr API key:  $READARR_API_KEY
    Prowlarr API key: $PROWLARR_API_KEY

    Nog te doen (kan niet worden geautomatiseerd zonder jouw eigen accounts):
    - Indexers toevoegen in Prowlarr (Settings > Indexers) -- dit zijn je eigen
      trackeraccounts, dat kan alleen jij invullen.
EOF
