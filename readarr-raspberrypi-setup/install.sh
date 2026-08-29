#!/usr/bin/env bash
# Eenmalige, zoveel mogelijk geautomatiseerde setup voor Readarr + Torbox +
# Dropbox-sync op een Raspberry Pi. Draai dit rechtstreeks op de Pi (via SSH
# over je bestaande Tailscale-verbinding), NIET lokaal.
#
#   ssh <gebruiker>@<tailscale-hostname-van-je-pi>
#   git clone https://github.com/Jasperdeveer/Jasperdeveer.git
#   cd Jasperdeveer/readarr-raspberrypi-setup
#   cp .env.example .env && nano .env      # vul TORBOX_EMAIL + TORBOX_API_KEY in
#   ./install.sh
set -euo pipefail

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SETUP_DIR/.env" ]; then
  echo "Geen .env gevonden. Maak 'm aan met: cp .env.example .env"
  echo "Vul daarna TORBOX_EMAIL en TORBOX_API_KEY in en draai dit script opnieuw."
  exit 1
fi
set -a
source "$SETUP_DIR/.env"
set +a

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
mkdir -p "$SETUP_DIR/config/readarr" "$SETUP_DIR/config/prowlarr" "$SETUP_DIR/config/decypharr" "$SETUP_DIR/library" "$SETUP_DIR/logs"
sudo mkdir -p /mnt/torbox
sudo chown "$USER" /mnt/torbox

echo "==> Torbox rclone-remote (WebDAV) automatisch aanmaken..."
if [ -z "${TORBOX_EMAIL:-}" ] || [ -z "${TORBOX_API_KEY:-}" ]; then
  echo "!! TORBOX_EMAIL / TORBOX_API_KEY ontbreken in .env -- sla Torbox-remote over."
  echo "   Vul .env aan en draai dan: rclone config create torbox webdav url=https://webdav.torbox.app vendor=other user=<email> pass=\$(rclone obscure <apikey>)"
elif rclone listremotes | grep -q '^torbox:$'; then
  echo "  Remote 'torbox' bestaat al, sla over."
else
  rclone config create torbox webdav \
    url=https://webdav.torbox.app \
    vendor=other \
    user="$TORBOX_EMAIL" \
    pass="$(rclone obscure "$TORBOX_API_KEY")"
  echo "  OK. (Controleer bij problemen de actuele WebDAV-host/credentials in je"
  echo "   Torbox-account onder Settings -> Integrations -- Torbox kan dit wijzigen.)"
fi

echo "==> Dropbox rclone-remote..."
if rclone listremotes | grep -q '^dropbox:$'; then
  echo "  Remote 'dropbox' bestaat al, sla over."
else
  echo "  !! Dit is de enige stap die ik niet voor je kan automatiseren: Dropbox"
  echo "     vereist een interactieve OAuth-login met jouw account."
  echo "     Start nu de configuratie (volg de link, log in bij Dropbox):"
  echo ""
  rclone config create dropbox dropbox
fi

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
EnvironmentFile=-${SETUP_DIR}/.env
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

echo "==> Mount + sync-timer starten..."
sudo systemctl enable --now rclone-torbox-mount.service
sudo systemctl enable --now dropbox-sync.timer

echo "==> Readarr + Prowlarr + Decypharr starten..."
cd "$SETUP_DIR"
docker compose up -d

TAILSCALE_IP="$(command -v tailscale >/dev/null 2>&1 && tailscale ip -4 2>/dev/null || echo 'TAILSCALE-IP-VAN-JE-PI')"

cat <<WIZARDEOF

==> EENMALIGE HANDMATIGE STAP: Decypharr opzetten (Torbox-koppeling)
    Torbox heeft geen ingebouwde qBittorrent-compatibele API -- Decypharr
    vertaalt tussen de qBittorrent-API (die Readarr verwacht) en Torbox's
    eigen API. Dit vereist een korte, interactieve setup-wizard die niet
    volledig gescript kan worden. Ga naar:

      http://${TAILSCALE_IP}:8282

    en doorloop de wizard:
      - Debrid provider: Torbox, met je TORBOX_API_KEY (staat in .env)
      - Usenet: overslaan, tenzij je dat expliciet wilt (zie README.md)
      - Mount type: "None" -- we gebruiken de bestaande rclone-mount op
        /mnt/torbox, Decypharr hoeft zelf niets te mounten

    Druk daarna op Enter om verder te gaan met de automatische configuratie.
WIZARDEOF
read -r -p ""

echo "==> Readarr + Prowlarr automatisch configureren (root folder, Decypharr-downloadclient, Prowlarr<->Readarr sync)..."
"$SETUP_DIR/scripts/configure-apps.sh" || echo "!! configure-apps.sh niet volledig gelukt -- draai 'm later opnieuw: ./scripts/configure-apps.sh"

cat <<EOF

==> Installatie klaar.

  Readarr:   http://${TAILSCALE_IP}:8787
  Prowlarr:  http://${TAILSCALE_IP}:9696
  Decypharr: http://${TAILSCALE_IP}:8282

Nog te doen (dit vereist echt jouw eigen accounts/keuzes, kan niet worden
geautomatiseerd):
  - Indexers toevoegen in Prowlarr (Settings -> Indexers) met je eigen
    trackeraccounts.

Zie README.md voor details en troubleshooting.
EOF
