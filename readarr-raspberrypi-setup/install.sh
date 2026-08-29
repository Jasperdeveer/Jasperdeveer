#!/usr/bin/env bash
# Eenmalige host-setup voor Readarr + Torbox + Dropbox-sync op een Raspberry Pi.
# Draai dit script rechtstreeks op de Pi (via SSH over Tailscale), NIET lokaal.
#
#   ssh pi@<tailscale-hostname>
#   git clone <deze-repo>
#   cd Jasperdeveer/readarr-raspberrypi-setup
#   ./install.sh
set -euo pipefail

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Controleer Docker..."
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is niet gevonden. Installeer het eerst, bv.:"
  echo "  curl -fsSL https://get.docker.com | sudo sh"
  echo "  sudo usermod -aG docker \$USER   # daarna opnieuw inloggen"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin ontbreekt. Installeer via: sudo apt install docker-compose-plugin"
  exit 1
fi

echo "==> Controleer rclone..."
if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone wordt geinstalleerd (vereist sudo)..."
  curl -fsSL https://rclone.org/install.sh | sudo bash
fi

echo "==> Mappen aanmaken..."
mkdir -p "$SETUP_DIR/config/readarr" "$SETUP_DIR/config/prowlarr" "$SETUP_DIR/library" "$SETUP_DIR/logs"
sudo mkdir -p /mnt/torbox

echo "==> systemd unit voor de Torbox WebDAV-mount schrijven..."
sudo tee /etc/systemd/system/rclone-torbox-mount.service >/dev/null <<EOF
[Unit]
Description=rclone mount van Torbox WebDAV naar /mnt/torbox
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User=${USER}
ExecStart=/usr/bin/rclone mount torbox: /mnt/torbox \\
  --config=/home/${USER}/.config/rclone/rclone.conf \\
  --allow-other \\
  --vfs-cache-mode=full \\
  --dir-cache-time=1m
ExecStop=/bin/fusermount -uz /mnt/torbox
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "==> systemd service + timer voor de Dropbox-sync schrijven..."
sudo tee /etc/systemd/system/dropbox-sync.service >/dev/null <<EOF
[Unit]
Description=Sync Readarr-bibliotheek naar Dropbox

[Service]
Type=oneshot
User=${USER}
ExecStart=${SETUP_DIR}/scripts/sync-to-dropbox.sh
EOF

sudo tee /etc/systemd/system/dropbox-sync.timer >/dev/null <<EOF
[Unit]
Description=Periodieke Dropbox-sync voor Readarr

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload

cat <<'EOF'

==> Basis-installatie klaar. Vervolgstappen (handmatig, eenmalig):

1. Configureer rclone remotes:
     rclone config
   - Maak remote "torbox" aan (type: webdav), url https://webdav.torbox.app,
     vendor "other", user = je Torbox e-mailadres, pass = je Torbox API key.
     (Controleer host/credentials in je Torbox account -> Settings -> Integrations,
      deze kunnen door Torbox worden aangepast.)
   - Maak remote "dropbox" aan (type: dropbox) en volg de OAuth-link.
     Geen browser op de Pi? Draai "rclone authorize dropbox" op je laptop en
     plak het resultaat terug in de Pi-config.

2. Start de mount + sync-timer:
     sudo systemctl enable --now rclone-torbox-mount.service
     sudo systemctl enable --now dropbox-sync.timer

3. Start Readarr + Prowlarr:
     cp .env.example .env   # pas PUID/PGID/TZ aan indien nodig
     docker compose up -d

4. Open de webinterfaces via je Tailscale-IP:
     http://<tailscale-ip>:8787   (Readarr)
     http://<tailscale-ip>:9696   (Prowlarr)

Zie README.md voor het configureren van Torbox als download-client en
Prowlarr-indexers binnen Readarr.
EOF
