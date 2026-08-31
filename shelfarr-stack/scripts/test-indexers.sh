#!/usr/bin/env bash
# Laat Prowlarr zélf zoeken en toont wat elke indexer teruggeeft.
#
#   ./scripts/test-indexers.sh "dune"
#   ./scripts/test-indexers.sh "the secret of secrets"
#
# Dit gaat buiten Shelfarr om. Komen hier resultaten uit maar blijft Shelfarr
# op not_found staan, dan ligt het aan Shelfarr's filtering (taal, formaat,
# min_match_confidence). Komt hier niets uit, dan hebben je indexers het boek
# domweg niet — of ze antwoorden niet, bijvoorbeeld omdat ze de VPN-exit
# blokkeren of achter een Cloudflare-check zitten.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

QUERY="${*:-}"
[ -z "$QUERY" ] && { echo "Gebruik: $0 \"zoekterm\"" >&2; exit 1; }

DOCKER="docker"
command -v docker >/dev/null 2>&1 && { docker info >/dev/null 2>&1 || DOCKER="sudo docker"; }

PKEY=$($DOCKER exec prowlarr cat /config/config.xml 2>/dev/null \
       | sed -n 's:.*<ApiKey>\(.*\)</ApiKey>.*:\1:p' | head -1)
[ -z "$PKEY" ] && { echo "API-key niet te lezen uit de prowlarr-container" >&2; exit 1; }

printf '\033[1mProwlarr zoekt: %s\033[0m\n' "$QUERY"
printf 'categorieen 7000 (boeken) + 3030 (audioboeken), even geduld…\n\n'

curl -sS --max-time 90 --get \
  -H "X-Api-Key: $PKEY" \
  --data-urlencode "query=$QUERY" \
  --data-urlencode "categories=7000" \
  --data-urlencode "categories=3030" \
  --data-urlencode "type=search" \
  "http://localhost:9696/api/v1/search" 2>/dev/null \
| python3 -c '
import json, sys
try:
    rel = json.load(sys.stdin)
except Exception:
    print("  kon het antwoord niet lezen — draait Prowlarr en klopt de poort?"); sys.exit()
if not isinstance(rel, list):
    print("  " + str(rel)[:200]); sys.exit()
if not rel:
    print("  Nul resultaten bij alle indexers.")
    print()
    print("  Dat is geen Shelfarr-probleem. Kijk in Prowlarr onder System -> Events")
    print("  of de indexers antwoorden: publieke trackers blokkeren vaak VPN-exits,")
    print("  en Cloudflare-checks vragen om FlareSolverr *in Prowlarr* (Settings ->")
    print("  Indexers -> FlareSolverr op http://flaresolverr:8191).")
    sys.exit()

per = {}
for r in rel:
    per.setdefault(r.get("indexer", "?"), []).append(r)

print("  %-28s %s" % ("indexer", "resultaten"))
for name in sorted(per, key=lambda n: -len(per[n])):
    print("  %-28s %d" % (name[:28], len(per[name])))

print()
print("  Beste treffers op seeders:")
best = sorted(rel, key=lambda r: -(r.get("seeders") or 0))[:8]
for r in best:
    size = (r.get("size") or 0) / (1024*1024)
    print("   %4ds  %7.0f MB  %-18s %s" % (
        r.get("seeders") or 0, size, (r.get("indexer") or "?")[:18],
        (r.get("title") or "?")[:56]))
print()
print("  Totaal %d resultaten. Ziet hier iets bruikbaars tussen maar staat de" % len(rel))
print("  aanvraag op not_found, dan filtert Shelfarr het weg — check de taal van")
print("  de aanvraag en min_match_confidence.")
'
