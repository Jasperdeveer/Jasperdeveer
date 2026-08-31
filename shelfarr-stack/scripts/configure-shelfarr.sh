#!/usr/bin/env bash
# Zet de Shelfarr-configuratie die anders handwerk in de web-UI is: de indexer,
# de download client en de output paths. Leest de benodigde gegevens uit je
# draaiende stack, zodat je niks hoeft over te typen.
#
#   ./scripts/configure-shelfarr.sh
#   ./scripts/configure-shelfarr.sh --with-hardcover   # betere metadata (gratis token)
#   ./scripts/configure-shelfarr.sh --with-zlibrary    # Z-Library (eigen account)
#   ./scripts/configure-shelfarr.sh --with-anna        # FlareSolverr + Anna's Archive
#
# Draai dit ná `docker compose up -d` en nadat je je adminaccount hebt
# geregistreerd. Herhaald draaien is veilig: bestaande waarden worden bijgewerkt,
# niet gedupliceerd. Geheimen worden niet afgedrukt.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

WITH_ANNA=0
WITH_HARDCOVER=0
WITH_ZLIB=0
for arg in "$@"; do
  case "$arg" in
    --with-anna)      WITH_ANNA=1 ;;
    --with-hardcover) WITH_HARDCOVER=1 ;;
    --with-zlibrary)  WITH_ZLIB=1 ;;
    *) echo "onbekende optie: $arg" >&2; exit 1 ;;
  esac
done

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

HARDCOVER_TOKEN=""
if [ "$WITH_HARDCOVER" = 1 ]; then
  hdr "Hardcover"
  note "Gratis token via hardcover.app/account/api (account aanmaken, geen betaling)."
  note "Zonder token draait de zoekfunctie op Open Library alleen, en die mist veel."
  read -rsp "  API-token: " HARDCOVER_TOKEN; echo
  [ -n "$HARDCOVER_TOKEN" ] && note "token ingelezen (${#HARDCOVER_TOKEN} tekens)" \
                            || note "leeg gelaten — Hardcover blijft uit"
fi

# Z-Library wisselt regelmatig van domein. Deze lijst is actueel per 2026-08-31;
# Shelfarr probeert ze op volgorde en gebruikt de eerste die je login accepteert.
# Overschrijven kan zonder dit bestand aan te raken:
#   ZLIBRARY_URLS=$'https://nieuw.example\nhttps://ander.example' ./scripts/configure-shelfarr.sh --with-zlibrary
ZLIB_URLS="${ZLIBRARY_URLS:-https://z-library.sk
https://z-lib.sk
https://z-library.im
https://z-lib.fm
https://libb.la}"

ZLIB_EMAIL=""; ZLIB_PASS=""
if [ "$WITH_ZLIB" = 1 ]; then
  hdr "Z-Library"
  note "Directe downloads: geen indexer, geen Torbox, geen seeders nodig."
  note "Shelfarr eist e-mail én wachtwoord; zonder allebei blijft de bron uit."
  note "domeinen: $(printf '%s' "$ZLIB_URLS" | tr '\n' ' ')"
  read -rp  "  E-mail: " ZLIB_EMAIL
  read -rsp "  Wachtwoord: " ZLIB_PASS; echo
  if [ -n "$ZLIB_EMAIL" ] && [ -n "$ZLIB_PASS" ]; then
    note "ingelezen voor $ZLIB_EMAIL (${#ZLIB_PASS} tekens)"
  else
    note "onvolledig — Z-Library blijft uit"
    ZLIB_EMAIL=""; ZLIB_PASS=""
  fi
fi

FLARESOLVERR_URL=""
ANNA_ENABLED="false"
ANNA_KEY=""
if [ "$WITH_ANNA" = 1 ]; then
  hdr "FlareSolverr"
  if ! $DOCKER compose ps --status running 2>/dev/null | grep -q flaresolverr; then
    note "container draait nog niet — starten"
    grep -q '^COMPOSE_PROFILES=' .env \
      && sed -i 's/^COMPOSE_PROFILES=.*/COMPOSE_PROFILES=flaresolverr/' .env \
      || printf 'COMPOSE_PROFILES=flaresolverr\n' >> .env
    $DOCKER compose up -d flaresolverr || fail "FlareSolverr kwam niet op"
    note "even wachten tot Chromium klaar is…"
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      $DOCKER compose exec -T shelfarr sh -c \
        'wget -qO- --timeout=3 http://flaresolverr:8191/ >/dev/null 2>&1' && break
      sleep 3
    done
  fi
  if $DOCKER compose exec -T shelfarr sh -c \
       'wget -qO- --timeout=5 http://flaresolverr:8191/ >/dev/null 2>&1'; then
    FLARESOLVERR_URL="http://flaresolverr:8191"
    note "bereikbaar op $FLARESOLVERR_URL"
  else
    note "nog niet bereikbaar; controleer later met: docker compose logs flaresolverr"
    FLARESOLVERR_URL="http://flaresolverr:8191"
  fi

  hdr "Anna's Archive"
  note "Shelfarr gebruikt deze bron alleen met een member-API-key (donatie)."
  note "Zonder key blijft hij ongebruikt, ook als de toggle aanstaat."
  read -rsp "  API-key (leeg laten mag): " ANNA_KEY; echo
  ANNA_ENABLED="true"
  if [ -n "$ANNA_KEY" ]; then
    note "key ingelezen (${#ANNA_KEY} tekens)"
  else
    note "geen key — toggle gaat aan, maar de bron telt nog niet mee"
  fi
fi

hdr "Toepassen in Shelfarr"

# `docker compose exec` slaat de entrypoint over, en juist die zet de
# Active Record-encryptiesleutels in de omgeving — zonder hen weigert
# production.rb te booten. We laden ze hier uit dezelfde bestanden op het
# storage-volume, en laten rails als de `rails`-gebruiker draaien zodat de
# SQLite-hulpbestanden niet van root worden.
RUNNER='
[ -f /rails/storage/.encryption_keys ] && . /rails/storage/.encryption_keys
if [ -z "${SECRET_KEY_BASE:-}" ] && [ -f /rails/storage/.secret_key_base ]; then
  SECRET_KEY_BASE=$(cat /rails/storage/.secret_key_base)
  export SECRET_KEY_BASE
fi
if [ "$(id -u)" = "0" ] && command -v gosu >/dev/null 2>&1; then
  exec gosu rails bin/rails runner -
else
  exec bin/rails runner -
fi
'

$DOCKER compose exec -T \
  -e CFG_PROWLARR_URL="$PROWLARR_URL" \
  -e CFG_PROWLARR_KEY="$PROWLARR_KEY" \
  -e CFG_DECY_URL="$DECY_URL" \
  -e CFG_DECY_USER="$DECY_USER" \
  -e CFG_DECY_PASS="$DECY_PASS" \
  -e CFG_DOWNLOAD_LOCAL_PATH="$DOWNLOAD_LOCAL_PATH" \
  -e CFG_WITH_ANNA="$WITH_ANNA" \
  -e CFG_HARDCOVER_TOKEN="$HARDCOVER_TOKEN" \
  -e CFG_ZLIB_EMAIL="$ZLIB_EMAIL" \
  -e CFG_ZLIB_URLS="$ZLIB_URLS" \
  -e CFG_ZLIB_PASS="$ZLIB_PASS" \
  -e CFG_FLARESOLVERR_URL="$FLARESOLVERR_URL" \
  -e CFG_ANNA_ENABLED="$ANNA_ENABLED" \
  -e CFG_ANNA_KEY="$ANNA_KEY" \
  shelfarr sh -c "$RUNNER" <<'RUBY'
require "net/http"

def put_setting(key, value)
  s = Setting.find_by(key: key)
  if s.nil?
    puts "  overgeslagen (bestaat niet): #{key}"
    return
  end
  s.typed_value = value
  s.save!
  secret = %w[key token password secret].any? { |w| key.include?(w) }
  shown = secret ? "***" : value.inspect
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
put_setting "enabled_languages",              [ "nl", "en" ]
put_setting "default_language",               "nl"

# Publiek domein, geen account of key nodig — altijd aan.
put_setting "gutenberg_enabled",              true
put_setting "librivox_enabled",               true

# Ruimere zoekresultaten; de defaults (20 en 10) zijn krap voor auteurs met
# veel titels of edities.
put_setting "open_library_search_limit",      40
put_setting "hardcover_search_limit",         25
put_setting "metadata_source",                "auto"

hc_token = ENV["CFG_HARDCOVER_TOKEN"].to_s.strip.sub(/\ABearer\s+/i, "")
unless hc_token.empty?
  put_setting "hardcover_api_token", hc_token
end

unless ENV["CFG_ZLIB_EMAIL"].to_s.empty? || ENV["CFG_ZLIB_PASS"].to_s.empty?
  put_setting "zlibrary_enabled",  true
  put_setting "zlibrary_url",      ENV["CFG_ZLIB_URLS"]
  put_setting "zlibrary_email",    ENV["CFG_ZLIB_EMAIL"]
  put_setting "zlibrary_password", ENV["CFG_ZLIB_PASS"]
end

if ENV["CFG_WITH_ANNA"] == "1"
  put_setting "flaresolverr_url",    ENV["CFG_FLARESOLVERR_URL"]
  put_setting "anna_archive_enabled", ENV["CFG_ANNA_ENABLED"] == "true"
  put_setting "anna_archive_api_key", ENV["CFG_ANNA_KEY"].to_s unless ENV["CFG_ANNA_KEY"].to_s.empty?
end

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

begin
  puts "  gutenberg  #{SettingsService.gutenberg_configured? ? 'actief' : 'uit'}"
  puts "  librivox   #{SettingsService.librivox_configured? ? 'actief' : 'uit'}"
  zl = SettingsService.zlibrary_configured?
  puts "  zlibrary   #{zl ? 'actief' : 'uit'}"
rescue StandardError => e
  puts "  bronnen    status onleesbaar: #{e.class}"
end

begin
  tok = Setting.find_by(key: "hardcover_api_token")&.value.to_s
  if tok.empty?
    puts "  hardcover  geen token — zoeken draait op Open Library alleen"
  else
    uri = URI("https://api.hardcover.app/v1/graphql")
    req = Net::HTTP::Post.new(uri)
    req["Authorization"] = "Bearer #{tok}"
    req["Content-Type"]  = "application/json"
    req.body = '{"query":"{ me { username } }"}'
    res = Net::HTTP.start(uri.host, uri.port, use_ssl: true, open_timeout: 10, read_timeout: 20) { |h| h.request(req) }
    body = res.body.to_s
    if res.code == "200" && !body.include?('"errors"')
      puts "  hardcover  HTTP 200 — token werkt (#{tok.length} tekens)"
    else
      puts "  hardcover  HTTP #{res.code} — token geweigerd (#{tok.length} tekens)"
      puts "             #{body[0, 140]}"
      puts "             Hardcover geeft lange JWT's uit die met eyJ beginnen;"
      puts "             is de jouwe korter, dan is hij waarschijnlijk afgekapt."
    end
  end
rescue StandardError => e
  puts "  hardcover  onbereikbaar: #{e.class} #{e.message}"
end

if ENV["CFG_WITH_ANNA"] == "1"
  begin
    uri = URI("#{ENV['CFG_FLARESOLVERR_URL']}/")
    res = Net::HTTP.start(uri.host, uri.port, open_timeout: 5, read_timeout: 15) { |h| h.request(Net::HTTP::Get.new(uri)) }
    puts "  flare      HTTP #{res.code} — bereikbaar"
  rescue StandardError => e
    puts "  flare      onbereikbaar: #{e.class} #{e.message}"
  end
  begin
    ok = SettingsService.anna_archive_configured?
    puts "  anna       #{ok ? 'actief' : 'toggle staat aan, maar zonder API-key gebruikt Shelfarr de bron niet'}"
  rescue StandardError => e
    puts "  anna       status onleesbaar: #{e.class}"
  end
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
