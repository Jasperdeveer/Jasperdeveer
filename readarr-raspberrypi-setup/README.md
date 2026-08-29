# Readarr-opvolger op je Raspberry Pi, met Torbox als downloadbron en sync naar Dropbox

Deze map bevat een kant-en-klare Docker Compose-stack + installatiescript om
een Readarr-opvolger op je Raspberry Pi te draaien, Torbox als downloadclient
te gebruiken, en de resulterende boeken automatisch naar Dropbox te syncen.
Getest en werkend op een Raspberry Pi OS Bullseye (64-bit kernel) systeem.

De Dropbox-doelmap: **`/Jasper de Veer/Readarr-Library`**.

## Architectuur

```
Torbox (WebDAV)  --rclone mount-->  /mnt/torbox  --bind mount-->  Readarr (import)
Torbox (echte API) <-- Decypharr (qBittorrent-mock) <-- Readarr (download client, start/monitor)
Readarr  --organiseert boeken naar--> ./library
./library  --rclone copy (timer)-->  Dropbox: /Jasper de Veer/Readarr-Library
Prowlarr --indexers--> Readarr (zoeken naar boeken; Torbox zoekt zelf niet)
```

Drie containers: `readarr` (de Readarr-opvolger), `prowlarr` (indexer-manager)
en `decypharr` (vertaalt tussen de qBittorrent-API die Readarr verwacht en
Torbox's eigen API — zie hieronder waarom die nodig is).

Torbox is geen *indexer* (zoekbron) maar een *downloadclient*: het haalt de
torrents op die Readarr via indexers vindt. Je hebt dus naast Torbox nog
gewoon indexers nodig (via Prowlarr) — dat is het enige stukje dat alleen jij
kan invullen, omdat het om jouw eigen trackeraccounts gaat.

## Twee belangrijke afwijkingen van een "standaard" Readarr-setup

### 1. Readarr zelf is dood — we draaien Bookshelf

Readarr is in juli 2025 door de makers gearchiveerd/stopgezet
(`github.com/linuxserver/docker-readarr`, gearchiveerd 6 juli 2025: "upstream
has decided to retire the project"). We draaien in plaats daarvan
**`ghcr.io/pennydreadful/bookshelf:hardcover`**: een actieve community-fork
met dezelfde Readarr-codebase, API en configstructuur (poort 8787, `/config`
volume), maar met Hardcover.app als metadata-bron in plaats van de kapotte
Goodreads-koppeling van het origineel. Voor Prowlarr en de REST API maakt dit
verder niets uit — alles hieronder werkt identiek aan "gewoon Readarr".

### 2. Torbox heeft geen eigen qBittorrent-API — Decypharr overbrugt dat

De aanname dat Torbox een eigen qBittorrent-compatibel endpoint aanbiedt
(`qbittorrent.torbox.app` ofzoiets) klopt niet — dat bestaat niet. Torbox
biedt alleen zijn eigen (WebDAV- en REST-)API's. Om Readarr toch gewoon "een
qBittorrent-downloadclient" te kunnen laten toevoegen, draait
**Decypharr** (`ghcr.io/sirrobot01/decypharr`) ertussen: het doet zich naar
Readarr toe voor als qBittorrent, en praat achter de schermen met Torbox's
echte API.

Decypharr's eigen mount-functies (die het downloaden zelf als virtueel
bestandssysteem aanbieden) gebruiken we niet — dat vereist FUSE +
`SYS_ADMIN`-rechten in de container, wat we liever vermijden. In plaats
daarvan staat Decypharr op **mount type "None"**: we vertrouwen op de
rclone-mount die we al hebben op `/mnt/torbox` (bind-mounted in de
`readarr`-container) voor het daadwerkelijk zien van de bestanden.

**Decypharr moet je één keer zelf via de webinterface opzetten** (setup-
wizard: `http://<pi-ip>:8282`) — dat kan niet volledig gescript worden.
`install.sh` pauzeert daarvoor en wacht op een Enter.

## Bekend Bullseye-probleem: SIGSYS-crashes door verouderde libseccomp2

Op Raspberry Pi OS Bullseye (2021, nog steeds veelgebruikt) is `libseccomp2`
te oud (2.5.1) voor recente containerimages die glibc 2.34+ gebruiken. De
32-bit (`armhf`) userspace van Bullseye draait `containerd`/`runc` die de
`clone3`-syscall niet correct kunnen filteren, waardoor containers direct
crashen met exit code 159 (SIGSYS) en vrijwel lege logs. Een gewone
`apt install --only-upgrade libseccomp2` lost dit niet op omdat Bullseye's
repo geen nieuwere versie heeft.

**Fix in `docker-compose.yml`:** `security_opt: [seccomp=unconfined]` op alle
drie de services. Dit schakelt seccomp-filtering voor deze containers uit —
een bewuste, beperkte security-trade-off (alleen deze 3 containers, niet de
hele host) totdat je OS een upgrade krijgt (Bullseye zelf is uit 2021 en
ontvangt op termijn geen updates meer).

## Stap 1 — Repo op de Pi zetten

```bash
ssh <gebruiker>@<tailscale-hostname-van-je-pi>
git clone https://github.com/Jasperdeveer/Jasperdeveer.git
cd Jasperdeveer/readarr-raspberrypi-setup
```

## Stap 2 — .env invullen

```bash
cp .env.example .env
nano .env
```

Vul `TORBOX_EMAIL` en `TORBOX_API_KEY` in (te vinden in je Torbox-account
onder **Settings → Integrations**). `PUID`/`PGID` moeten overeenkomen met de
eigenaar van de `./library`-map op de host, anders kan de container niet
schrijven (Readarr geeft dan een "Folder not writable"-fout bij het
toevoegen van de root folder).

## Stap 3 — Eén script: `./install.sh`

```bash
./install.sh
```

Dit doet automatisch:
1. Controleert/installeert Docker en rclone.
2. Maakt de Torbox rclone-remote (WebDAV) **non-interactief** aan met de
   gegevens uit `.env`.
3. Start de Dropbox rclone-configuratie — **interactief moment**: je krijgt
   een link, log in bij Dropbox en bevestig. (Geen browser op de Pi zelf?
   Draai op je laptop `rclone authorize dropbox` en plak het resultaat terug
   wanneer het script erom vraagt.)
4. Zet systemd-units klaar en start de Torbox-mount + de Dropbox-sync-timer
   (elke 30 minuten).
5. Start Readarr (Bookshelf) + Prowlarr + Decypharr via Docker Compose.
6. **Pauzeert voor de Decypharr-wizard** (zie hierboven) — eenmalig,
   interactief, kan niet gescript worden.
7. Wacht tot Readarr/Prowlarr hun API-key gegenereerd hebben en configureert
   dan automatisch, via hun REST API's:
   - root folder `/books` in Readarr
   - Decypharr als qBittorrent-compatibele downloadclient in Readarr
   - de app-koppeling Prowlarr → Readarr (voor indexer-sync)

## Stap 4 — Openen

```
http://<tailscale-ip-van-pi>:8787   (Readarr / Bookshelf)
http://<tailscale-ip-van-pi>:9696   (Prowlarr)
http://<tailscale-ip-van-pi>:8282   (Decypharr)
```

## Wat jij nog moet doen (kan echt niet geautomatiseerd worden)

- **Dropbox-login** tijdens `install.sh` (interactieve OAuth, eenmalig).
- **Decypharr-setup-wizard** tijdens `install.sh` (Torbox API-key invullen,
  mount type "None" kiezen, eenmalig).
- **Indexers toevoegen in Prowlarr** (Settings → Indexers): dit zijn jouw
  eigen trackeraccounts (bv. MyAnonamouse of andere boeken-indexers), dat kan
  alleen jij invullen. Prowlarr pusht ze daarna automatisch door naar Readarr
  dankzij de app-koppeling die `install.sh` al heeft gelegd.

Als de automatische Readarr/Prowlarr-koppeling niet lukt, kun je 'm los
opnieuw draaien:

```bash
./scripts/configure-apps.sh
```

## Optioneel: Usenet via Torbox's News Server

Torbox biedt naast torrent-caching ook een **News Server** (NNTP-toegang,
inloggegevens op `torbox.app/tools/`). Let op: dit is puur een Usenet-
*provider* (de "postbode") — Torbox levert **geen indexering**. Je hebt dus
nog steeds een eigen, apart betaald Usenet-indexer-abonnement nodig (zoals
NZBgeek of DrunkenSlug) om NZB's te kunnen vinden. Decypharr ondersteunt
native NNTP-streaming; de NNTP-gegevens vul je in bij Decypharr's
Usenet-stap, en de indexer voeg je toe in Prowlarr (die ondersteunt naast
torrent- ook Newznab/Usenet-indexers).

## Directe sync na import (optioneel, i.p.v. wachten op de timer)

In Readarr: **Settings → Connect → + → Custom Script**:

- Path: `/scripts/sync-to-dropbox.sh`
- Triggers: "On Import Complete" (en eventueel "On Upgrade")
- Environment variable op de trigger: `READARR_LIBRARY_DIR=/books` (want het
  script draait dan in de container, waar de bibliotheek op `/books` hangt in
  plaats van op het hostpad).

Voor de meeste gebruikers is de systemd-timer (elke 30 minuten, buiten de
container om) eenvoudiger en robuuster — dan hoef je dit niet te doen.

## Logs & troubleshooting

- Dropbox-sync log: `logs/dropbox-sync.log`
- Torbox-mount status: `systemctl status rclone-torbox-mount.service`
- Readarr/Prowlarr/Decypharr logs: `docker compose logs -f readarr prowlarr decypharr`
- App-koppeling opnieuw proberen: `./scripts/configure-apps.sh`
- Containers crashen direct (exit code 159, lege logs): zie het
  libseccomp2/Bullseye-probleem hierboven.
- "Folder '/books' is not writable": `PUID`/`PGID` in `.env` komt niet
  overeen met de eigenaar van `./library` op de host.
