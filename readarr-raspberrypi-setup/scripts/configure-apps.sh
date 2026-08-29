#!/usr/bin/env bash
# Automatisch Readarr + Prowlarr configureren via hun REST API's, zodat je dit
# niet handmatig in de webinterface hoeft te doen:
#  - root folder /books in Readarr
#  - Decypharr (Torbox-koppeling) als qBittorrent-compatibele downloadclient
#  - Prowlarr <-> Readarr app-sync
#
# Vereist dat je Decypharr EENMALIG zelf via de webinterface hebt opgezet
# (http://<pi>:8282 -- setup-wizard: debrid provider Torbox, mount type
# "None" omdat we de bestaande rclone-mount op /mnt/torbox al gebruiken).
# Dat kan niet worden gescript omdat het een interactieve wizard is.
#
# Wordt automatisch aangeroepen door install.sh nadat `docker compose up -d`
# is gedraaid. Losstaand opnieuw draaien kan ook: ./scripts/configure-apps.sh
set -uo pipefail

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$SETUP_DIR/.env" ] && set -a && source "$SETUP_DIR/.env" && set +a

READARR_URL="http://localhost:8787"
PROWLARR_URL="http://localhost:9696"
READARR_INTERNAL_URL="http://readarr:8787"
DECYPHARR_HOST="decypharr"
DECYPHARR_PORT="8282"

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
QUALITY_PROFILE_ID="$(curl -sf -H "X-Api-Key: $READARR_API_KEY" "$READARR_URL/api/v1/qualityprofile" | grep -oP '"id":\K[0-9]+' | head -1)"
METADATA_PROFILE_ID="$(curl -sf -H "X-Api-Key: $READARR_API_KEY" "$READARR_URL/api/v1/metadataprofile" | grep -oP '"id":\K[0-9]+' | head -1)"
curl -sf -X POST "$READARR_URL/api/v1/rootfolder" \
  -H "X-Api-Key: $READARR_API_KEY" -H "Content-Type: application/json" \
  -d "{\"path\":\"/books\",\"name\":\"Books\",\"defaultMetadataProfileId\":${METADATA_PROFILE_ID:-1},\"defaultQualityProfileId\":${QUALITY_PROFILE_ID:-1}}" >/dev/null \
  && echo "  OK" || echo "  overgeslagen (bestond al, of /books is niet schrijfbaar -- check PUID/PGID in docker-compose.yml en de eigenaar van ./library op de host)"

echo "==> Decypharr (Torbox) koppelen als downloadclient in Readarr..."
if curl -sf -o /dev/null "http://localhost:${DECYPHARR_PORT}"; then
  curl -sf -X POST "$READARR_URL/api/v1/downloadclient" \
    -H "X-Api-Key: $READARR_API_KEY" -H "Content-Type: application/json" \
    -d "{
      \"enable\": true,
      \"protocol\": \"torrent\",
      \"priority\": 1,
      \"name\": \"Decypharr (Torbox)\",
      \"implementation\": \"QBittorrent\",
      \"configContract\": \"QBittorrentSettings\",
      \"fields\": [
        {\"name\": \"host\", \"value\": \"${DECYPHARR_HOST}\"},
        {\"name\": \"port\", \"value\": ${DECYPHARR_PORT}},
        {\"name\": \"useSsl\", \"value\": false},
        {\"name\": \"username\", \"value\": \"${READARR_INTERNAL_URL}\"},
        {\"name\": \"password\", \"value\": \"${READARR_API_KEY}\"},
        {\"name\": \"category\", \"value\": \"readarr\"}
      ]
    }" >/dev/null \
    && echo "  OK" || echo "  mislukt of bestond al -- controleer handmatig in Readarr (Settings > Download Clients)"
else
  echo "  Decypharr (poort ${DECYPHARR_PORT}) is nog niet bereikbaar."
  echo "  Doorloop eerst de eenmalige setup-wizard: http://<pi-ip>:${DECYPHARR_PORT}"
  echo "  (debrid provider: Torbox, mount type: None) en draai dit script daarna opnieuw."
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
      {\"name\": \"baseUrl\", \"value\": \"${READARR_INTERNAL_URL}\"},
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
    - Optioneel: Usenet via Torbox's News Server (torbox.app/tools/) instellen
      in Decypharr's usenet-sectie -- vereist ook een eigen Usenet-indexer
      (zoals NZBgeek), Torbox levert alleen de NNTP-toegang, geen indexering.
EOF
