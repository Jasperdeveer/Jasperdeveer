#!/usr/bin/env bash
# Synct de boekenbibliotheken eenmalig naar Dropbox via rclone.
# Wordt aangeroepen door de systemd-timer (periodiek) of door Readarr's
# "Custom Script" connect-hook (direct na een import).
#
# Twee bibliotheken, elk naar een eigen Dropbox-map:
#   library/   — beheerd door Bookshelf
#   shelfarr/  — beheerd door Shelfarr (audiobooks/ en ebooks/)
# Een map die niet bestaat wordt overgeslagen, niet als fout gemeld.
#
# Te overschrijven met READARR_LIBRARY_DIR, DROPBOX_REMOTE,
# SHELFARR_LIBRARY_DIR en SHELFARR_DROPBOX_REMOTE.
set -euo pipefail

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$SETUP_DIR/logs"
LOG_FILE="$LOG_DIR/dropbox-sync.log"

mkdir -p "$LOG_DIR"

sync_dir() {
  local label="$1" src="$2" dest="$3"

  if [ ! -d "$src" ]; then
    echo "[$(date -Is)] $label overgeslagen: $src bestaat niet" >>"$LOG_FILE"
    return 0
  fi

  echo "[$(date -Is)] $label gestart: $src -> $dest" >>"$LOG_FILE"
  rclone copy "$src" "$dest" \
    --update \
    --transfers=4 \
    --checkers=8 \
    --log-file="$LOG_FILE" \
    --log-level INFO
  echo "[$(date -Is)] $label klaar" >>"$LOG_FILE"
}

sync_dir "Bookshelf" \
  "${READARR_LIBRARY_DIR:-$SETUP_DIR/library}" \
  "${DROPBOX_REMOTE:-dropbox:Jasper de Veer/Readarr-Library}"

sync_dir "Shelfarr" \
  "${SHELFARR_LIBRARY_DIR:-$SETUP_DIR/shelfarr}" \
  "${SHELFARR_DROPBOX_REMOTE:-dropbox:Jasper de Veer/Shelfarr-Library}"
