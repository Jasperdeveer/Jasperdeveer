# Readarr op je Raspberry Pi, met Torbox als downloadbron en sync naar Dropbox

Deze map bevat een kant-en-klare Docker Compose-stack + installatiescript om
Readarr op je Raspberry Pi te draaien, Torbox als downloadclient te gebruiken,
en de resulterende boeken automatisch naar Dropbox te syncen.

**Belangrijk:** dit script moet je zelf op je Raspberry Pi draaien (via SSH,
over je bestaande Tailscale-verbinding). Deze Claude-sessie draait in een
losse cloud-omgeving en heeft geen toegang tot jouw Tailnet of Pi — ik kan dit
dus niet voor je uitvoeren, wel volledig voor je klaarzetten.

## Architectuur

```
Torbox (WebDAV)  --rclone mount-->  /mnt/torbox  --bind mount-->  Readarr (import)
Torbox (qBittorrent-compatible API) <-- Readarr (download client, start/monitor)
Readarr  --organiseert boeken naar--> ./library
./library  --rclone copy (timer of custom-script hook)-->  Dropbox
Prowlarr --indexers--> Readarr (zoeken naar boeken; Torbox zoekt zelf niet)
```

Torbox is geen *indexer* (zoekbron) maar een *downloadclient*: het haalt de
torrents/nzb's op die Readarr via indexers vindt. Je hebt dus naast Torbox nog
gewoon indexers nodig (via Prowlarr, of rechtstreeks in Readarr).

## Stap 1 — Repo op de Pi zetten

```bash
ssh <gebruiker>@<tailscale-hostname-van-je-pi>
git clone https://github.com/Jasperdeveer/Jasperdeveer.git
cd Jasperdeveer/readarr-raspberrypi-setup
```

## Stap 2 — Installatiescript draaien

```bash
./install.sh
```

Dit script:
- controleert of Docker + Docker Compose aanwezig zijn (en zegt hoe je ze
  installeert als dat niet zo is);
- installeert `rclone` als dat nog niet aanwezig is;
- maakt de benodigde mappen aan (`config/`, `library/`, `logs/`, `/mnt/torbox`);
- zet systemd-units klaar voor de Torbox-mount en de periodieke Dropbox-sync.

Aan het eind print het script de vervolgstappen (hieronder ook beschreven).

## Stap 3 — rclone remotes configureren

Eenmalig, interactief:

```bash
rclone config
```

- **Remote "torbox"** (type `webdav`): url `https://webdav.torbox.app`,
  vendor `other`, gebruikersnaam = je Torbox-account e-mail, wachtwoord = je
  Torbox API key. Controleer host en inloggegevens in je Torbox-account onder
  **Settings → Integrations**, want dit kan door Torbox worden aangepast.
- **Remote "dropbox"** (type `dropbox`): volg de OAuth-link in de terminal.
  Geen browser beschikbaar op de Pi zelf? Draai `rclone authorize dropbox` op
  je laptop/telefoon-browser en plak het token terug in de config op de Pi.

## Stap 4 — Mount en sync-timer activeren

```bash
sudo systemctl enable --now rclone-torbox-mount.service
sudo systemctl enable --now dropbox-sync.timer
```

Controleer:

```bash
systemctl status rclone-torbox-mount.service
ls /mnt/torbox
systemctl list-timers dropbox-sync.timer
```

De timer synct standaard elke 30 minuten. Wil je dat een sync direct na een
import gebeurt in plaats van te wachten op de timer? Zie "Directe sync na
import" hieronder.

## Stap 5 — Containers starten

```bash
cp .env.example .env   # pas PUID/PGID/TZ aan indien nodig (id -u / id -g)
docker compose up -d
```

- Readarr: `http://<tailscale-ip-van-pi>:8787`
- Prowlarr: `http://<tailscale-ip-van-pi>:9696`

## Stap 6 — Prowlarr indexers koppelen

1. Open Prowlarr, voeg je indexers toe (publieke boeken-indexers of iets als
   MyAnonamouse als je daar een account hebt).
2. Ga naar **Settings → Apps** in Prowlarr en koppel Readarr (interne URL
   `http://readarr:8787`, API-key uit Readarr → Settings → General).
3. Prowlarr pusht de indexers automatisch door naar Readarr.

## Stap 7 — Torbox als downloadclient in Readarr

In Readarr: **Settings → Download Clients → +  → qBittorrent** (Torbox biedt
een qBittorrent-compatibele API, dus je configureert het als een qBittorrent-
client):

- Host: `qbittorrent.torbox.app` (controleer de actuele hostnaam in je Torbox
  account onder Integrations — dit kan wijzigen)
- Poort: `443`, SSL aan
- Gebruikersnaam / wachtwoord: je Torbox API key (zie Torbox-documentatie
  voor de exacte huidige velden)
- Categorie: bv. `readarr`

## Stap 8 — Root folder instellen

In Readarr: **Settings → Media Management → Root Folders** → voeg `/books`
toe (dat is de container-mount van `./library` op de Pi). Zet ook het
downloadpad in de download-client-config naar `/torbox` (de read-only mount
van de Torbox WebDAV) zodat Readarr voltooide bestanden daar kan importeren.

## Directe sync na import (optioneel, i.p.v. wachten op de timer)

In Readarr: **Settings → Connect → +  → Custom Script**:

- Path: `/scripts/sync-to-dropbox.sh`
- Triggers: "On Import Complete" (en eventueel "On Upgrade")

Let op: dit script draait dan *in de container*, terwijl het pad naar
`library/` in het script relatief is aan de hostmap. Als je dit gebruikt,
overschrijf dan `READARR_LIBRARY_DIR=/books` als environment variable op de
Custom Script-trigger in Readarr, zodat het script binnen de container het
juiste pad gebruikt. Voor de meeste gebruikers is de systemd-timer (elke 30
minuten, buiten de container om) eenvoudiger en robuuster — dan hoef je dit
niet te doen.

## Logs & troubleshooting

- Dropbox-sync log: `logs/dropbox-sync.log`
- Torbox-mount status: `systemctl status rclone-torbox-mount.service`
- Readarr/Prowlarr logs: `docker compose logs -f readarr prowlarr`

## Wat ik (Claude) al heb voorbereid

- Alle configuratiebestanden in deze map (`docker-compose.yml`, `install.sh`,
  `scripts/sync-to-dropbox.sh`, `.env.example`).

## Wat jij nog moet doen op de Pi zelf

- `install.sh` draaien, `rclone config` (Torbox + Dropbox OAuth — vereist
  jouw inloggegevens), Torbox-downloadclient en Prowlarr-indexers instellen
  in de webinterfaces. Dit zijn stappen die alleen jij, met jouw accounts en
  fysieke/SSH-toegang tot de Pi, kunt uitvoeren.
