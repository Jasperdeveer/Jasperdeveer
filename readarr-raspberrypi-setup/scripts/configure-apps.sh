#!/usr/bin/env bash
# Automatisch Readarr + Prowlarr + Decypharr configureren via hun REST API's,
# zodat je dit niet handmatig in de webinterfaces hoeft te doen:
#  - Decypharr's config.json patchen (ebook-bestandstypen toestaan, downloads
#    echt lokaal wegschrijven i.p.v. symlinken -- vereist omdat we geen eigen
#    mount gebruiken, zie README.md)
#  - Prowlarr's eigen "Application URL" op de gluetun-sidecar zetten, zodat
#    indexers die naar Readarr worden gesynct een bereikbaar adres krijgen
#  - root folder /books in Readarr
#  - Decypharr als qBittorrent-compatibele downloadclient in Readarr
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
# Prowlarr en Decypharr delen het netwerk van de gluetun-sidecar (VPN), dus
# zijn voor andere containers bereikbaar via de naam "gluetun", niet hun eigen
# containernaam.
DECYPHARR_HOST="gluetun"
DECYPHARR_PORT="8282"
PROWLARR_INTERNAL_URL="http://gluetun:9696"

extract_api_key() {
  grep -oP '(?<=<ApiKey>)[^<]+' "$1" 2>/dev/null || true
}

echo "==> Decypharr's config.json patchen (ebook-bestandstypen + download-actie)..."
DECYPHARR_CONFIG="$SETUP_DIR/config/decypharr/config.json"
for _ in $(seq 1 30); do
  [ -f "$DECYPHARR_CONFIG" ] && break
  sleep 2
done
if [ -f "$DECYPHARR_CONFIG" ]; then
  python3 - "$DECYPHARR_CONFIG" << "PYEOF"
import json, sys
path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)
ebook_types = ["epub", "mobi", "azw", "azw3", "pdf", "cbz", "cbr", "djvu", "fb2", "txt", "rtf", "cb7", "cbt"]
existing = set(cfg.get("allowed_file_types", []))
cfg["allowed_file_types"] = sorted(existing | set(ebook_types))
# "symlink" verwacht een eigen mount (rclone/dfs); wij draaien mount type
# "None" en laten Decypharr de bestanden echt lokaal downloaden.
cfg["default_download_action"] = "download"
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
print("  OK -- allowed_file_types:", len(cfg["allowed_file_types"]), "types, default_download_action:", cfg["default_download_action"])
PYEOF
  docker restart decypharr >/dev/null 2>&1 && echo "  decypharr herstart om de nieuwe config te laden"
else
  echo "  !! $DECYPHARR_CONFIG bestaat nog niet -- doorloop eerst de Decypharr-wizard"
  echo "     (http://<pi-ip>:${DECYPHARR_PORT}) en draai dit script daarna opnieuw."
fi

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

echo "==> Prowlarr's Application URL op de gluetun-sidecar zetten..."
# Zonder dit genereert Prowlarr indexer-proxy-URL's met zijn eigen
# containernaam ("prowlarr"), die niet resolvet vanuit Readarr omdat Prowlarr
# via network_mode: service:gluetun draait en dus geen eigen netwerknaam heeft.
python3 - "$PROWLARR_URL" "$PROWLARR_API_KEY" "$PROWLARR_INTERNAL_URL" << "PYEOF"
import json, sys, urllib.request

base_url, api_key, app_url = sys.argv[1], sys.argv[2], sys.argv[3]
req = urllib.request.Request(f"{base_url}/api/v1/config/host", headers={"X-Api-Key": api_key})
with urllib.request.urlopen(req) as resp:
    cfg = json.load(resp)
cfg["applicationUrl"] = app_url
cfg_id = cfg["id"]
body = json.dumps(cfg).encode()
req2 = urllib.request.Request(f"{base_url}/api/v1/config/host/{cfg_id}", data=body, method="PUT",
                               headers={"X-Api-Key": api_key, "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req2) as resp2:
        print("  OK", resp2.status)
except urllib.error.HTTPError as e:
    print("  FAILED", e.code, e.read().decode()[:300])
PYEOF

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
      {\"name\": \"prowlarrUrl\", \"value\": \"${PROWLARR_INTERNAL_URL}\"},
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
    - Optioneel: metadataprofiel-taal aanpassen (Settings > Metadata Profiles
      in Readarr) als je liever niet-Engelstalige edities krijgt.
EOF
