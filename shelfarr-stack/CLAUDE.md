# Werkcontext: Shelfarr-stack

Deze map bevat een Docker Compose-stack die Shelfarr toevoegt aan een bestaande
media-stack op een Raspberry Pi. Draai je vanaf de Pi zelf, dan kun je afmaken wat
vanuit een cloud-sessie niet kon: de echte stack uitlezen en `.env` kloppend maken.

## De bestaande stack — vastgesteld, niet gokken

- Raspberry Pi, bereikbaar via Tailscale op `100.120.136.112`.
- **64-bit kernel (`aarch64`), 32-bit userland (`armhf`), Docker-daemon `arm`.**
  Docker pullt daardoor uit zichzelf armv7-images, die voor Shelfarr niet bestaan;
  vandaar `platform: linux/arm64` op elke service. Arm64-*containers* draaien wel,
  omdat de kernel 64-bit is. Software die je rechtstreeks op de Pi installeert moet
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

## Wat nog open staat

1. **Welk hostpad hoort bij Decypharr's `/app/downloads`, en staan daar symlinks?**
   Onder `/mnt` staan er geen, dus ze zitten in die downloadmap of Decypharr
   importeert rechtstreeks uit `/mnt/torbox` (939 items). `./scripts/stack-check.sh`
   dumpt de container-mounts en zoekt daar naar symlinks.
   - Wijzen symlinks naar `/mnt/torbox/...` → `DOWNLOADS_PATH` en
     `DOWNLOADS_CONTAINER_PATH` moeten die map 1-op-1 zichtbaar maken; kies zo nodig
     `/mnt` als gedeelde bovenliggende map. Een symlink breekt zodra de container het
     doel op een ander pad ziet.
2. **Waar de Dropbox-timer vandaan synct** → daarbinnen horen `AUDIOBOOKS_PATH` en
   `EBOOKS_PATH` te liggen, anders lopen Shelfarr-boeken niet mee naar Dropbox.
3. **Wat Bookshelf als root folder gebruikt** → Shelfarr moet daar níét in schrijven.

## Werkwijze

- Draai `./scripts/make-env.sh --dry-run` als eerste; die leidt alles af behalve de
  bibliotheekpaden. `./scripts/stack-check.sh` geeft het volledige beeld.
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
