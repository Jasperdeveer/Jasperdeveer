# Werkcontext: Shelfarr-stack

Deze map bevat een Docker Compose-stack die Shelfarr toevoegt aan een bestaande
media-stack op een Raspberry Pi. Draai je vanaf de Pi zelf, dan kun je afmaken wat
vanuit een cloud-sessie niet kon: de echte stack uitlezen en `.env` kloppend maken.

## De bestaande stack — vastgesteld, niet gokken

- Raspberry Pi, bereikbaar via Tailscale op `100.120.136.112`.
- **Prowlarr** als indexer-manager, poort 9696.
- **Readarr** op poort 8787. Dit is de app die Shelfarr overneemt. Readarr is op
  27 juni 2025 gearchiveerd omdat de Goodreads-metadata-API verdween; Shelfarr
  gebruikt Open Library en Hardcover en heeft dat probleem niet.
- **Decypharr (Torbox)** als download client, op host `gluetun` poort 8282, mét
  gebruikersnaam en wachtwoord. Readarr gebruikt category `readarr`.
- Readarr heeft **geen** Remote Path Mappings staan: Decypharr en Readarr zien de
  bestanden op precies hetzelfde pad.
- Torbox-opslag is via **rclone** gemount op `/mnt/torbox`.
- Een **Dropbox-timer** synct de bibliotheek door naar Dropbox.

## Wat nog open staat

1. **Waar zet Decypharr zijn symlinks neer, en waarheen wijzen ze?**
   `./scripts/stack-check.sh` beantwoordt dit (read-only, maskeert secrets).
   - Symlinks binnen `/mnt/torbox` → laat `DOWNLOADS_PATH` en
     `DOWNLOADS_CONTAINER_PATH` op `/mnt/torbox`.
   - Symlinks elders onder `/mnt` → zet beide op `/mnt`, zodat elk pad 1-op-1
     klopt. Een symlink breekt zodra de container het doel op een ander pad ziet.
2. **Netwerknaam van gluetun** → `ARR_NETWORK` in `.env`. Zonder dat kan Shelfarr
   `gluetun:8282` niet bereiken.
3. **Waar de Dropbox-timer vandaan synct** → daarbinnen horen `AUDIOBOOKS_PATH`
   en `EBOOKS_PATH` te liggen, anders lopen Shelfarr-boeken niet mee.
4. **Zit Prowlarr ook achter gluetun?** Dan is de indexer-URL `http://gluetun:9696`
   in plaats van `http://prowlarr:9696`.

## Werkwijze

- Draai `./scripts/stack-check.sh` als eerste.
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
