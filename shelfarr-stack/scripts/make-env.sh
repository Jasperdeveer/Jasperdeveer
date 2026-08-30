#!/usr/bin/env bash
# Leest de draaiende stack uit en schrijft daaruit een .env.
#
#   ./scripts/make-env.sh            # schrijft .env (weigert te overschrijven)
#   ./scripts/make-env.sh --force    # overschrijft een bestaande .env
#   ./scripts/make-env.sh --dry-run  # print alleen wat het zou schrijven

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

MODE="write"
case "${1:-}" in
  --force)   MODE="force" ;;
  --dry-run) MODE="dry" ;;
  "")        ;;
  *) echo "onbekende optie: $1" >&2; exit 1 ;;
esac

if [ -f .env ] && [ "$MODE" = "write" ]; then
  echo ".env bestaat al. Gebruik --force om te overschrijven, of --dry-run om te kijken." >&2
  exit 1
fi

DOCKER="docker"
command -v docker >/dev/null 2>&1 && { docker info >/dev/null 2>&1 || DOCKER="sudo docker"; }

note() { printf '  %s\n' "$1"; }

echo "Uitlezen…"

PUID=$(id -u); PGID=$(id -g)
TZ_VAL=$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo Europe/Amsterdam)
note "PUID/PGID       $PUID/$PGID, tijdzone $TZ_VAL"

ARR_NETWORK=$($DOCKER inspect gluetun -f '{{range $n,$_ := .NetworkSettings.Networks}}{{$n}}{{end}}' 2>/dev/null)
if [ -n "$ARR_NETWORK" ]; then
  note "gluetun-netwerk $ARR_NETWORK"
else
  ARR_NETWORK="readarr-raspberrypi-setup_default"
  note "gluetun niet gevonden — ARR_NETWORK op $ARR_NETWORK gezet, controleer dit"
fi

TORBOX_MOUNT=$(mount | awk '$5 ~ /fuse\.rclone/ {print $3; exit}')
TORBOX_MOUNT=${TORBOX_MOUNT:-/mnt/torbox}
note "rclone-mount    $TORBOX_MOUNT"

# Decypharr's downloadmap op de host, en waar eventuele symlinks heen wijzen.
DL=$($DOCKER inspect decypharr -f '{{range .Mounts}}{{if eq .Destination "/app/downloads"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)
LINK_TARGET=""
if [ -n "$DL" ] && [ -d "$DL" ]; then
  first_link=$(find "$DL" -maxdepth 4 -type l -print -quit 2>/dev/null)
  [ -n "$first_link" ] && LINK_TARGET=$(readlink "$first_link" 2>/dev/null)
fi

NEED_SYMLINK_OVERRIDE=0
if [ -n "$DL" ]; then
  DOWNLOADS_PATH="$DL"
  note "downloadmap     $DL  (Decypharr /app/downloads)"
  case "$DL" in
    "$TORBOX_MOUNT"|"$TORBOX_MOUNT"/*)
      note "                ligt in de rclone-mount, één mount volstaat" ;;
    *)
      if [ -n "$LINK_TARGET" ]; then
        note "symlink wijst   $LINK_TARGET"
        case "$LINK_TARGET" in
          "$TORBOX_MOUNT"/*) NEED_SYMLINK_OVERRIDE=1
            note "                buiten de mount én symlinks erheen: tweede mount nodig" ;;
        esac
      else
        note "                geen symlinks aangetroffen"
      fi ;;
  esac
else
  DOWNLOADS_PATH="$TORBOX_MOUNT"
  note "downloadmap     geen bind-mount op /app/downloads; $TORBOX_MOUNT gebruikt"
fi

COMPOSE_FILE="docker-compose.yml:docker-compose.arr-network.yml"
[ "$NEED_SYMLINK_OVERRIDE" = 1 ] && COMPOSE_FILE="$COMPOSE_FILE:docker-compose.symlinks.yml"

# Bibliotheek: kandidaten voorstellen, maar niet gokken.
LIB_HINT=$($DOCKER inspect readarr -f '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' 2>/dev/null \
           | grep -iE 'book|librar|media|calibre' | head -3)
LIB_BASE=$(printf '%s' "$LIB_HINT" | head -1 | awk '{print $1}')
if [ -n "$LIB_BASE" ]; then
  LIB_PARENT=$(dirname "$LIB_BASE")
  AUDIOBOOKS_PATH="$LIB_PARENT/shelfarr/audiobooks"
  EBOOKS_PATH="$LIB_PARENT/shelfarr/ebooks"
else
  AUDIOBOOKS_PATH="/mnt/ssd/media/shelfarr/audiobooks"
  EBOOKS_PATH="/mnt/ssd/media/shelfarr/ebooks"
fi
DATA_PATH="$PWD/data"

OUT=$(cat <<EOF
# Gegenereerd door scripts/make-env.sh op $(date -Iseconds)

SHELFARR_VERSION=2026.08.24.1
DOCKER_PLATFORM=linux/arm64

PUID=$PUID
PGID=$PGID
TZ=$TZ_VAL

DATA_PATH=$DATA_PATH

# CONTROLEER: deze moeten liggen in de map die je Dropbox-timer synct,
# en niet in de root folder van Bookshelf.
AUDIOBOOKS_PATH=$AUDIOBOOKS_PATH
EBOOKS_PATH=$EBOOKS_PATH

DOWNLOADS_PATH=$DOWNLOADS_PATH
DOWNLOADS_CONTAINER_PATH=$DOWNLOADS_PATH
DOWNLOADS_MOUNT_OPTS=ro,rslave
SYMLINK_TARGET_ROOT=$TORBOX_MOUNT

SHELFARR_PORT=5056
BIND_ADDRESS=0.0.0.0
HTTP_PORT=80

ARR_NETWORK=$ARR_NETWORK
COMPOSE_FILE=$COMPOSE_FILE

AUDIOBOOKSHELF_PORT=13378
AUDIOBOOKSHELF_CONFIG_PATH=$PWD/audiobookshelf/config
AUDIOBOOKSHELF_METADATA_PATH=$PWD/audiobookshelf/metadata
FLARESOLVERR_LOG_LEVEL=info
CHOWN_ON_START=auto
EOF
)

echo
if [ "$MODE" = "dry" ]; then
  echo "--- .env zoals het geschreven zou worden ---"
  printf '%s\n' "$OUT"
  exit 0
fi

printf '%s\n' "$OUT" > .env
echo "Geschreven: $PWD/.env"
echo
[ -n "$LIB_HINT" ] && { echo "Bibliotheek-mounts van Bookshelf, ter controle:"; printf '%s\n' "$LIB_HINT"; echo; }
cat <<'EOT'
Nog even zelf nakijken:
  AUDIOBOOKS_PATH / EBOOKS_PATH  — moeten binnen je Dropbox-syncmap liggen en
                                   buiten Bookshelf's root folder.

Daarna:
  mkdir -p "$(grep ^AUDIOBOOKS_PATH .env | cut -d= -f2)" "$(grep ^EBOOKS_PATH .env | cut -d= -f2)"
  docker compose up -d
  docker compose logs -f shelfarr
EOT
