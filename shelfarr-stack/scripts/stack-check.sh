#!/usr/bin/env bash
# Leest je bestaande stack uit en print precies wat er nodig is om Shelfarr
# te configureren. Alleen lezen — dit verandert niets.
#
# Geheimen (API-keys, wachtwoorden, tokens) worden gemaskeerd, dus de uitvoer
# is veilig om te delen.
#
#   ./scripts/stack-check.sh
#   ./scripts/stack-check.sh | tee ~/stack-check.txt

set -uo pipefail

DOCKER="docker"
command -v docker >/dev/null 2>&1 && { docker info >/dev/null 2>&1 || DOCKER="sudo docker"; }

mask() {
  sed -E 's/("?(api[_-]?key|apikey|token|password|passwd|secret|pass)"?[[:space:]]*[:=][[:space:]]*"?)[^",[:space:]]+/\1***GEMASKEERD***/Ig'
}

hdr() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }

hdr "Platform"
echo "kernel-arch  : $(uname -m)   (zegt alleen iets over de kernel)"
echo "userland     : $(dpkg --print-architecture 2>/dev/null || echo onbekend)   <-- moet arm64 zijn, niet armhf"
echo "word-size    : $(getconf LONG_BIT)-bit"
darch=$($DOCKER version --format '{{.Server.Arch}}' 2>/dev/null | tr -d '[:space:]')
echo "docker-arch  : ${darch:-onbekend}   <-- bepaalt welke images gepulld worden"
echo "kernel       : $(uname -r)"
[ -r /etc/os-release ] && . /etc/os-release && echo "os           : ${PRETTY_NAME:-onbekend}"
echo "uid/gid      : PUID=$(id -u) PGID=$(id -g)"
echo "tijdzone     : $(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo onbekend)"

hdr "Containers en gepubliceerde poorten"
ps_out=$($DOCKER ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' 2>/dev/null)
if [ -n "$ps_out" ]; then
  if command -v column >/dev/null 2>&1; then
    printf '%s\n' "$ps_out" | column -t -s $'\t'
  else
    printf '%s\n' "$ps_out" | tr '\t' '|'
  fi
else
  echo "(geen containers zichtbaar — draait Docker, en heb je rechten?)"
fi

hdr "Netwerk van gluetun  →  dit is de waarde voor ARR_NETWORK"
for c in gluetun prowlarr readarr decypharr; do
  nets=$($DOCKER inspect "$c" -f '{{range $n,$_ := .NetworkSettings.Networks}}{{$n}} {{end}}' 2>/dev/null)
  mode=$($DOCKER inspect "$c" -f '{{.HostConfig.NetworkMode}}' 2>/dev/null)
  [ -n "$nets$mode" ] && printf '%-12s netwerk: %-28s mode: %s\n' "$c" "${nets:-–}" "${mode:-–}"
done

hdr "Decypharr-config (gemaskeerd)"
cfg=""
for m in $($DOCKER inspect decypharr -f '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' 2>/dev/null); do
  [ -f "$m/config.json" ] && cfg="$m/config.json" && break
  [ -f "$m" ] && case "$m" in *.json) cfg="$m"; break;; esac
done
if [ -z "$cfg" ]; then
  cfg=$(find /opt /srv /home /mnt /var/lib -maxdepth 4 -name config.json -path '*decypharr*' 2>/dev/null | head -1)
fi
if [ -n "$cfg" ] && [ -r "$cfg" ]; then
  echo "gevonden: $cfg"
  grep -iE '"(path|folder|download_folder|dir|url|host|port|use_auth|username|categories|name)"' "$cfg" | mask
else
  echo "config.json niet gevonden — kijk zelf in de Decypharr-UI onder Settings."
fi

hdr "Mounts onder /mnt"
mount | grep -E ' on /mnt' | mask || echo "(geen)"

hdr "Wat staat er in de mount, en waar wijzen de symlinks heen?"
for d in /mnt/*/; do
  [ -d "$d" ] || continue
  n=$(ls -A "$d" 2>/dev/null | wc -l)
  printf '%-28s %s items\n' "$d" "$n"
done
echo
echo "-- symlinks (dit is het antwoord op 'waar zet Decypharr ze neer') --"
links=$(find /mnt -maxdepth 5 -type l -printf '%p  ->  %l\n' 2>/dev/null | head -15)
if [ -n "$links" ]; then
  printf '%s\n' "$links"
else
  echo "(geen symlinks onder /mnt — Decypharr importeert dan rechtstreeks uit de mount,"
  echo " of zet ze ergens anders neer; kijk in Readarr → Activity → History bij een boek)"
fi

hdr "rclone-proces en zijn vlaggen"
pgrep -a rclone 2>/dev/null | mask || echo "(rclone draait niet als los proces — mogelijk in een container)"

hdr "Klaar"
cat <<'EOT'
Wat hieruit volgt voor .env:
  ARR_NETWORK              = het netwerk van gluetun hierboven
  DOWNLOADS_PATH           = de map waar de symlinks staan
  DOWNLOADS_CONTAINER_PATH = hetzelfde pad, of /mnt als de symlinks buiten de
                             mount staan en naar een andere map onder /mnt wijzen
EOT
