#!/usr/bin/env bash
# Synct de Readarr-bibliotheek eenmalig naar Dropbox via rclone.
# Wordt aangeroepen door de systemd-timer (periodiek) of door Readarr's
# "Custom Script" connect-hook (direct na een import).
set -euo pipefail

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${READARR_LIBRARY_DIR:-$SETUP_DIR/library}"
DEST="${DROPBOX_REMOTE:-dropbox:Readarr-Library}"
LOG_DIR="$SETUP_DIR/logs"
LOG_FILE="$LOG_DIR/dropbox-sync.log"

mkdir -p "$LOG_DIR"

echo "[$(date -Is)] Sync gestart: $SRC -> $DEST" >>"$LOG_FILE"

rclone copy "$SRC" "$DEST" \
  --update \
  --transfers=4 \
  --checkers=8 \
  --log-file="$LOG_FILE" \
  --log-level INFO

echo "[$(date -Is)] Sync klaar" >>"$LOG_FILE"
