#!/usr/bin/env bash
# Eén overzicht van de hele keten: containers, schijf, de rclone-mount, de
# aanvragen in Shelfarr en de Dropbox-timer.
#
#   ./scripts/status.sh
#
# Voor de aanvragen is een API-token nodig. Zet die één keer weg:
#   echo 'shf_JOUW_ECHTE_TOKEN' > .shelfarr-token && chmod 600 .shelfarr-token
# of geef hem mee als SHELFARR_TOKEN in de omgeving. Zonder token werkt de
# rest gewoon, alleen het aanvragenoverzicht valt weg.
#
# Elke minuut laten meekijken kan met:  watch -n 60 ./scripts/status.sh

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

DOCKER="docker"
command -v docker >/dev/null 2>&1 && { docker info >/dev/null 2>&1 || DOCKER="sudo docker"; }

hdr() { printf '\n\033[1m%s\033[0m\n' "$1"; }
ok()  { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad() { printf '  \033[31m✗\033[0m %s\n' "$1"; }
inf() { printf '    %s\n' "$1"; }

PORT=$(sed -n 's/^SHELFARR_PORT=//p' .env 2>/dev/null | tail -1); PORT=${PORT:-5056}
MOUNT=$(sed -n 's/^DOWNLOADS_CONTAINER_PATH=//p' .env 2>/dev/null | tail -1); MOUNT=${MOUNT:-/mnt/torbox}

hdr "Containers"
for c in shelfarr flaresolverr audiobookshelf; do
  state=$($DOCKER inspect "$c" -f '{{.State.Status}}{{if .State.Health}} ({{.State.Health.Status}}){{end}}' 2>/dev/null)
  [ -z "$state" ] && continue
  case "$state" in
    running*unhealthy*) bad "$c — $state" ;;
    running*)           ok  "$c — $state" ;;
    *)                  bad "$c — $state" ;;
  esac
done
for c in gluetun prowlarr decypharr readarr; do
  state=$($DOCKER inspect "$c" -f '{{.State.Status}}' 2>/dev/null)
  [ -n "$state" ] && { [ "$state" = running ] && ok "$c — $state" || bad "$c — $state"; }
done

hdr "Schijf"
df -h / | awk 'NR==2 {printf "    root  %s van %s gebruikt (%s vrij)\n", $3, $2, $4}'
use=$(df --output=pcent / | tail -1 | tr -dc '0-9')
[ "${use:-0}" -ge 90 ] && bad "root zit op ${use}% — imports gaan stuklopen"

hdr "Downloadmount"
n=$($DOCKER compose exec -T shelfarr sh -c "ls -1 '$MOUNT' 2>/dev/null | wc -l" 2>/dev/null | tr -dc '0-9')
if [ -n "$n" ] && [ "$n" -gt 0 ]; then
  ok "$MOUNT zichtbaar in de container — $n items"
else
  bad "$MOUNT is leeg of onzichtbaar in de container"
  inf "mount-propagation of --allow-other; zie README stap 4"
fi

hdr "Bibliotheek"
for v in AUDIOBOOKS_PATH EBOOKS_PATH; do
  p=$(sed -n "s/^$v=//p" .env 2>/dev/null | tail -1)
  [ -z "$p" ] && continue
  if [ -d "$p" ]; then
    inf "$(printf '%-16s' "${v%_PATH}") $(find "$p" -type f 2>/dev/null | wc -l) bestanden  ($p)"
  else
    bad "$p bestaat niet"
  fi
done

hdr "Aanvragen"
TOKEN="${SHELFARR_TOKEN:-}"
[ -z "$TOKEN" ] && [ -r .shelfarr-token ] && TOKEN=$(tr -d '[:space:]' < .shelfarr-token)
if [ -z "$TOKEN" ]; then
  inf "geen token — zie de kop van dit script"
elif [ "$TOKEN" = "shf_..." ]; then
  bad "de placeholder uit de documentatie staat nog in .shelfarr-token"
  inf "maak een echt token onder Profile -> API tokens en zet dat erin"
else
  resp=$(curl -sS --max-time 10 -w '\n%{http_code}' -H "Authorization: Bearer $TOKEN" \
         "http://localhost:${PORT}/api/v1/requests?limit=200" 2>/dev/null)
  code=$(printf '%s' "$resp" | tail -1)
  body=$(printf '%s' "$resp" | sed '$d')
  case "$code" in
    401|403)
      bad "token geweigerd (HTTP $code) — vervangen of ingetrokken?" ;;
    ""|000)
      bad "geen antwoord van localhost:${PORT} — draait de container en klopt SHELFARR_PORT?" ;;
    200)
      printf '%s' "$body" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print("    onverwacht antwoord (token verlopen of ingetrokken?)"); sys.exit()
reqs = data.get("requests")
if reqs is None:
    print("    " + str(data.get("errors") or data)[:160]); sys.exit()
if not reqs:
    print("    nog geen aanvragen"); sys.exit()
counts = {}
for r in reqs:
    counts[r.get("status", "?")] = counts.get(r.get("status", "?"), 0) + 1
for s in ["pending","searching","downloading","processing","completed","not_found","failed","awaiting_purchase"]:
    if s in counts:
        print(f"    {s:<18} {counts[s]}")
stuck = [r for r in reqs if r.get("status") in ("failed","not_found")]
for r in stuck[:5]:
    book = r.get("book") or {}
    t = (r.get("title") or book.get("title") or "?")[:48]
    st = r.get("status")
    print("      ! %s: %s" % (st, t))
' ;;
    *)
      bad "onverwachte HTTP $code van de API" ;;
  esac
fi

hdr "Dropbox-sync"
if systemctl list-timers --all --no-pager 2>/dev/null | grep -q dropbox-sync.timer; then
  systemctl list-timers --all --no-pager 2>/dev/null | awk '/dropbox-sync.timer/ {print "    volgende: "$1" "$2" "$3"   ("$4" "$5")"}'
  res=$(systemctl show dropbox-sync.service -p Result --value 2>/dev/null)
  if [ "$res" = "success" ]; then
    ok "laatste run: success"
  else
    bad "laatste run: ${res:-onbekend}"
    journalctl -u dropbox-sync.service -n 5 --no-pager -o cat 2>/dev/null \
      | sed 's/^/      /' || inf "journalctl gaf niets terug"
  fi
else
  inf "geen dropbox-sync.timer gevonden"
fi
echo
