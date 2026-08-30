#!/usr/bin/env bash
# Zet de Shelfarr-configuratie die anders handwerk in de web-UI is: de indexer,
# de download client en de output paths. Leest de benodigde gegevens uit je
# draaiende stack, zodat je niks hoeft over te typen.
#
#   ./scripts/configure-shelfarr.sh
#
# Draai dit ná `docker compose up -d` en nadat je je adminaccount hebt
# geregistreerd. Herhaald draaien is veilig: bestaande waarden worden bijgewerkt,
# niet gedupliceerd. Geheimen worden niet afgedrukt.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

DOCKER="docker"
command -v docker >/dev/null 2>&1 && { docker info >/dev/null 2>&1 || DOCKER="sudo docker"; }

fail() { printf '\033[1mAfgebroken:\033[0m %s\n' "$1" >&2; exit 1; }
note() { printf '  %s\n' "$1"; }
hdr()  { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }

[ -f .env ] || fail "geen .env — draai eerst ./scripts/make-env.sh"
# shellcheck disable=SC1091
DOWNLOAD_LOCAL_PATH=$(sed -n 's/^DOWNLOADS_CONTAINER_PATH=//p' .env | tail -1)
DOWNLOAD_LOCAL_PATH=${DOWNLOAD_LOCAL_PATH:-/mnt/torbox}

$DOCKER compose ps --status running 2>/dev/null | grep -q shelfarr \
  || fail "de shelfarr-container draait niet — start met: docker compose up -d"

hdr "Prowlarr"
PROWLARR_URL="http://gluetun:9696"
PROWLARR_KEY=$($DOCKER exec prowlarr cat /config/config.xml 2>/dev/null \
               | sed -n 's:.*<ApiKey>\(.*\)</ApiKey>.*:\1:p' | head -1)
if [ -n "$PROWLARR_KEY" ]; then
  note "API-key gevonden (${#PROWLARR_KEY} tekens), URL $PROWLARR_URL"
else
  note "API-key niet uit de container te lezen."
  read -rp "  Plak Prowlarr's API-key (Settings -> General): " PROWLARR_KEY
  [ -n "$PROWLARR_KEY" ] || fail "zonder API-key kan de indexer niet ingesteld worden"
fi

hdr "Decypharr"
DECY_URL="http://gluetun:8282"
DECY_USER=""; DECY_PASS=""

# Bron 1: de download client-instellingen van Bookshelf. Die werken aantoonbaar.
BOOKSHELF_CFG=$($DOCKER inspect readarr -f '{{range .Mounts}}{{if eq .Destination "/config"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)
if [ -n "$BOOKSHELF_CFG" ] && command -v python3 >/dev/null 2>&1; then
  creds=$(python3 - "$BOOKSHELF_CFG" <<'PY' 2>/dev/null
import glob, json, sqlite3, sys
for db in glob.glob(sys.argv[1] + "/*.db"):
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = con.execute("select Settings from DownloadClients").fetchall()
    except Exception:
        continue
    for (raw,) in rows:
        try:
            cfg = json.loads(raw)
        except Exception:
            continue
        u, p = cfg.get("username", ""), cfg.get("password", "")
        if u or p:
            print(f"{u}\t{p}")
            sys.exit(0)
PY
)
  if [ -n "$creds" ]; then
    DECY_USER=$(printf '%s' "$creds" | cut -f1)
    DECY_PASS=$(printf '%s' "$creds" | cut -f2)
    note "inloggegevens overgenomen uit Bookshelf"
  fi
fi

# Bron 2: Decypharr's eigen config.
if [ -z "$DECY_PASS" ]; then
  DECY_CFG=$(find "$HOME" -maxdepth 6 -name config.json -path '*decypharr*' 2>/dev/null | head -1)
  if [ -n "$DECY_CFG" ]; then
    DECY_USER=$(sed -n 's/.*"username"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$DECY_CFG" | head -1)
    DECY_PASS=$(sed -n 's/.*"password"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$DECY_CFG" | head -1)
    [ -n "$DECY_PASS" ] && note "inloggegevens uit $DECY_CFG"
  fi
fi

# Bron 3: vragen.
if [ -z "$DECY_PASS" ]; then
  note "niet automatisch te vinden."
  read -rp "  Decypharr gebruikersnaam: " DECY_USER
  read -rsp "  Decypharr wachtwoord: " DECY_PASS; echo
fi
[ -n "$DECY_PASS" ] && note "wachtwoord ingelezen (${#DECY_PASS} tekens), URL $DECY_URL"

hdr "Toepassen in Shelfarr"
$DOCKER compose exec -T \
  -e CFG_PROWLARR_URL="$PROWLARR_URL" \
  -e CFG_PROWLARR_KEY="$PROWLARR_KEY" \
  -e CFG_DECY_URL="$DECY_URL" \
  -e CFG_DECY_USER="$DECY_USER" \
  -e CFG_DECY_PASS="$DECY_PASS" \
  -e CFG_DOWNLOAD_LOCAL_PATH="$DOWNLOAD_LOCAL_PATH" \
  shelfarr bin/rails runner - <<'RUBY'
require "net/http"

def put_setting(key, value)
  s = Setting.find_by(key: key)
  if s.nil?
    puts "  overgeslagen (bestaat niet): #{key}"
    return
  end
  s.typed_value = value
  s.save!
  shown = key.include?("key") || key.include?("token") ? "***" : value.inspect
  puts "  #{key} = #{shown}"
end

puts "Instellingen:"
put_setting "indexer_provider",               "prowlarr"
put_setting "prowlarr_url",                   ENV["CFG_PROWLARR_URL"]
put_setting "prowlarr_api_key",               ENV["CFG_PROWLARR_KEY"]
put_setting "audiobook_output_path",          "/audiobooks"
put_setting "ebook_output_path",              "/ebooks"
put_setting "download_local_path",            ENV["CFG_DOWNLOAD_LOCAL_PATH"]
put_setting "completed_download_import_mode", "copy"
put_setting "enabled_languages",              [ "en", "nl" ]

puts "\nDownload client:"
dc = DownloadClient.find_or_initialize_by(name: "Decypharr (Torbox)")
dc.client_type = "decypharr"
dc.url         = ENV["CFG_DECY_URL"]
dc.username    = ENV["CFG_DECY_USER"].to_s
dc.password    = ENV["CFG_DECY_PASS"].to_s
dc.category    = "shelfarr"
dc.enabled     = true
dc.priority    = 0 if dc.priority.nil?
dc.save!
puts "  #{dc.name}: #{dc.client_type} op #{dc.url}, category #{dc.category}"

puts "\nVerbindingen:"
begin
  uri = URI("#{ENV['CFG_PROWLARR_URL']}/api/v1/system/status")
  req = Net::HTTP::Get.new(uri)
  req["X-Api-Key"] = ENV["CFG_PROWLARR_KEY"]
  res = Net::HTTP.start(uri.host, uri.port, open_timeout: 10, read_timeout: 10) { |h| h.request(req) }
  puts "  prowlarr   HTTP #{res.code}#{res.code == '200' ? ' — OK' : ' — controleer URL en API-key'}"
rescue StandardError => e
  puts "  prowlarr   onbereikbaar: #{e.class} #{e.message}"
end

begin
  puts "  decypharr  #{dc.test_connection ? 'OK' : 'faalt — controleer inloggegevens'}"
rescue StandardError => e
  puts "  decypharr  fout: #{e.class} #{e.message}"
end

puts "\nZichtbaar voor de container:"
[ "/audiobooks", "/ebooks", ENV["CFG_DOWNLOAD_LOCAL_PATH"] ].each do |p|
  n = Dir.exist?(p) ? Dir.children(p).size : nil
  puts "  #{p.ljust(14)} #{n.nil? ? 'BESTAAT NIET' : "#{n} items"}"
end
RUBY

rc=$?
hdr "Klaar"
if [ $rc -eq 0 ]; then
  cat <<'EOT'
Wat hierboven op OK staat, is klaar. Wat nog met de hand moet:

  - Aanvragen doe je in de UI; auto-selectie staat bewust uit.
  - Controleer of /audiobooks en /ebooks binnen je Dropbox-syncmap vallen.
EOT
else
  echo "De rails-stap gaf een fout. Bekijk: docker compose logs --tail 40 shelfarr"
fi
