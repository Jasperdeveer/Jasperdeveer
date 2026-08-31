# Werkcontext: Shelfarr-stack

Deze map bevat een Docker Compose-stack die Shelfarr toevoegt aan een bestaande
media-stack op een Raspberry Pi. Draai je vanaf de Pi zelf, dan kun je afmaken wat
vanuit een cloud-sessie niet kon: de echte stack uitlezen en `.env` kloppend maken.

## De bestaande stack — vastgesteld, niet gokken

- Raspberry Pi, bereikbaar via Tailscale op `100.120.136.112`.
- **64-bit kernel (`aarch64`), 32-bit userland (`armhf`), Docker-daemon `arm`.**
  Docker pullt daardoor uit zichzelf armv7-images, die voor Shelfarr niet bestaan;
  vandaar `platform: linux/arm64` op elke service. Arm64-*containers* draaien wel,
  omdat de kernel 64-bit is, maar het seccomp-filter wordt voor arm32 gebouwd en
  doodt ze met SIGSYS (`exit 159`) — daarvoor is `docker-compose.compat.yml`. Software die je rechtstreeks op de Pi installeert moet
  armhf zijn — Claude Code kan hier dus niet draaien.
- OS: Raspbian 11 (bullseye), PUID/PGID 1000, TZ Europe/Amsterdam.
- **Bookshelf** (`ghcr.io/pennydreadful/bookshelf:hardcover`) op poort 8787 — een
  actief onderhouden Readarr-revival met Hardcover-metadata, géén dood project.
  Shelfarr komt ernaast, niet in de plaats van.
- **gluetun** (`qmcgaw/gluetun`) in netwerk `readarr-raspberrypi-setup_default`,
  publiceert 8282 en 9696 op de host.
- **Prowlarr** en **Decypharr** delen gluetun's netwerk-namespace
  (`network_mode: container:<gluetun>`). Binnen dat netwerk heten ze allebei
  `gluetun`: Prowlarr is `http://gluetun:9696`, Decypharr `http://gluetun:8282`.
- Decypharr-config: `~/Jasperdeveer/readarr-raspberrypi-setup/config/decypharr/config.json`,
  met `use_auth: true`, `download_folder: /app/downloads`, remote-naam `torbox`.
  Bookshelf gebruikt category `readarr`; Shelfarr krijgt `shelfarr`.
- Bookshelf heeft **geen** Remote Path Mappings: paden zijn aan beide kanten gelijk.
- **rclone**: `rclone mount torbox: /mnt/torbox --allow-other --vfs-cache-mode=full
  --dir-cache-time=1m`, uid/gid 1000. Die vlaggen zijn goed; niet aanpassen.
- Ook op de Pi: pihole (poorten 53/80/443).
- Een **Dropbox-timer** synct de bibliotheek door naar Dropbox.

## De downloadketen — uitgezocht, niet meer open

Decypharr mount `config/decypharr` op `/app`, dus zijn `download_folder`
`/app/downloads` is op de host `config/decypharr/downloads`. Bookshelf mount
diezelfde hostmap op **hetzelfde containerpad** `/app/downloads`, plus
`/mnt/torbox` op `/torbox`. Daarom heeft Bookshelf geen Remote Path Mapping nodig.

Shelfarr spiegelt die twee mounts, anders wijzen Decypharr's symlinks binnen
Shelfarr nergens heen:

| host | container | waarvoor |
|---|---|---|
| `…/config/decypharr/downloads` | `/app/downloads` | `download_local_path` |
| `/mnt/torbox` | `/torbox` | doel van de symlinks |

`/mnt/torbox` zelf is de rauwe Torbox-opslag: een platte lijst mediabestanden,
géén category-mappen. `download_local_path` mag daar dus nooit op wijzen —
Shelfarr zoekt in `<download_local_path>/<category>`.

`make-env.sh` leest beide paden uit de draaiende Bookshelf-container in plaats
van ze te raden, en schakelt `docker-compose.symlinks.yml` in.

## Nog te controleren

1. **Waar de Dropbox-timer vandaan synct.** `sync-to-dropbox.sh` doet inmiddels
   zowel `library/` als `shelfarr/`, elk naar een eigen Dropbox-map.
2. **Wat Bookshelf als root folder gebruikt** (`library/ -> /books`) → Shelfarr
   moet daar níét in schrijven.

## Werkwijze

- Draai `./scripts/make-env.sh --dry-run` als eerste; die leidt alles af behalve de
  bibliotheekpaden. `./scripts/stack-check.sh` geeft het volledige beeld.
- `./scripts/configure-shelfarr.sh` zet indexer, download client en output paths via
  `bin/rails runner` in de container. De JSON-API (`/api/v1`) dekt alleen requests;
  instellingen en download clients zitten achter de sessie-UI, vandaar die route.
- **Verander niets** aan Readarr, Prowlarr, gluetun, Decypharr of de rclone-mount.
  Shelfarr komt ernaast te staan, niet in de plaats van.
- Valideer compose-wijzigingen met `docker compose config` vóór je iets start.
- `README.md` is de gebruikersdocumentatie: houd die gelijk aan wat je in `.env`
  of de compose verandert.
- Committen op branch `claude/shelfarr-stack-integration-c4z6ki`.

## Vaste keuzes — niet omgooien zonder aanleiding

- **Import-modus `copy`.** Hardlinks kunnen niet tussen een rclone-mount en de SSD,
  en er wordt via een symlink geïmporteerd. `move` zou uit de Torbox-opslag wissen.
- **De downloadmount is `ro,rslave`.** `rslave` is verplicht: een FUSE-mount die na
  Docker wordt aangekoppeld is anders onzichtbaar in de container.
- **Category `shelfarr`**, los van Readarr's `readarr`, anders pakken beide apps
  elkaars downloads op.
- **Optionele containers achter compose-profiles.** Op een Pi telt elk stukje RAM.
