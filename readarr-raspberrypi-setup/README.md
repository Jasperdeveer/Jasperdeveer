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
                        Decypharr + Prowlarr --netwerk van--> gluetun (NordVPN-sidecar)
Decypharr --downloadt echte bestanden naar--> ./config/decypharr/downloads --gedeeld volume--> Readarr (import)
Readarr  --organiseert boeken naar--> ./library
./library  --rclone copy (timer)-->  Dropbox: /Jasper de Veer/Readarr-Library
Prowlarr --indexers--> Readarr (zoeken naar boeken; Torbox zoekt zelf niet)
```

Vier containers: `readarr` (de Readarr-opvolger), `prowlarr` (indexer-manager),
`decypharr` (vertaalt tussen de qBittorrent-API die Readarr verwacht en
Torbox's eigen API) en `gluetun` (VPN-sidecar, zie hieronder).

Torbox is geen *indexer* (zoekbron) maar een *downloadclient*: het haalt de
torrents op die Readarr via indexers vindt. Je hebt dus naast Torbox nog
gewoon indexers nodig (via Prowlarr) — dat is het enige stukje dat alleen jij
kan invullen, omdat het om jouw eigen trackeraccounts gaat.

## Belangrijke afwijkingen van een "standaard" Readarr-setup

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
daarvan staat Decypharr op **mount type "None"**, met
**`default_download_action: "download"`**: Decypharr downloadt de bestanden
dan echt lokaal naar `/app/downloads` (i.p.v. te symlinken naar een mount die
er niet is). Dat pad is als gedeeld volume gekoppeld in zowel `decypharr` als
`readarr` (`./config/decypharr/downloads:/app/downloads`), zodat Readarr de
kant-en-klare bestanden kan zien en importeren.

Decypharr's standaard `allowed_file_types`-lijst bevat alleen video/audio-
extensies (voor de Sonarr/Radarr-doelgroep) — **geen ebook-formaten**.
Zonder aanpassing filtert Decypharr dus stilzwijgend élk boek weg, met een
cryptische `"no valid download links available"`-fout tot gevolg. Beide
aanpassingen (download-actie + ebook-extensies zoals epub/mobi/pdf/cbz)
worden automatisch toegepast door `./scripts/configure-apps.sh` op
Decypharr's `config.json`, na de eenmalige setup-wizard.

**Decypharr moet je één keer zelf via de webinterface opzetten** (setup-
wizard: `http://<pi-ip>:8282`) — dat kan niet volledig gescript worden.
`install.sh` pauzeert daarvoor en wacht op een Enter.

### 3. Prowlarr en Decypharr draaien achter een NordVPN-sidecar (gluetun)

Voor privacy (je ISP kan anders zien dat je verkeer naar indexer-sites en
Torbox's API stuurt) routeren `prowlarr` en `decypharr` via een
`gluetun`-container (`network_mode: service:gluetun`) die verbinding maakt
met NordVPN via OpenVPN. `readarr` zelf staat hier **buiten** — die praat
alleen met containers binnen het thuisnetwerk en hoeft niet door de VPN.

Belangrijke gevolgen van deze netwerkopzet:
- Andere containers bereiken Prowlarr/Decypharr voortaan via de naam
  **`gluetun`**, niet via `prowlarr`/`decypharr` (die hebben geen eigen
  netwerkidentiteit meer). `configure-apps.sh` regelt dit automatisch, zowel
  voor Readarr's downloadclient-instelling als voor Prowlarr's eigen
  "Application URL" (nodig zodat de indexer-URL's die naar Readarr worden
  gesynct ook echt bereikbaar zijn).
- **`prowlarr` en `decypharr` starten pas als `gluetun` gezond is.** Zonder
  geldige NordVPN-credentials in `.env` blijft `gluetun` voor altijd
  "unhealthy" en komen deze twee containers dus nooit op. Vul
  `NORDVPN_OPENVPN_USER`/`NORDVPN_OPENVPN_PASSWORD` in vóór je
  `docker compose up -d` draait.
- NordVPN's WireGuard-sleutel is niet handmatig op te halen via hun
  webinterface (alleen IKEv2/OpenVPN stonden er). We gebruiken daarom
  **OpenVPN** met NordVPN's "Service credentials" (een apart
  gebruikersnaam/wachtwoord-paar voor handmatige configuraties, te vinden op
  `https://my.nordaccount.com/dashboard/nordvpn/manual-configuration/` →
  "Set up NordVPN manually" — dit zijn niet je normale account-inloggegevens).

## Bekend Bullseye-probleem: SIGSYS-crashes door verouderde libseccomp2

Op Raspberry Pi OS Bullseye (2021, nog steeds veelgebruikt) is `libseccomp2`
te oud (2.5.1) voor recente containerimages die glibc 2.34+ gebruiken. De
32-bit (`armhf`) userspace van Bullseye draait `containerd`/`runc` die de
`clone3`-syscall niet correct kunnen filteren, waardoor containers direct
crashen met exit code 159 (SIGSYS) en vrijwel lege logs. Een gewone
`apt install --only-upgrade libseccomp2` lost dit niet op omdat Bullseye's
repo geen nieuwere versie heeft.

**Fix in `docker-compose.yml`:** `security_opt: [seccomp=unconfined]` op alle
services met een eigen netwerknaamruimte. Dit schakelt seccomp-filtering voor
deze containers uit — een bewuste, beperkte security-trade-off (alleen deze
containers, niet de hele host) totdat je OS een upgrade krijgt (Bullseye zelf
is uit 2021 en ontvangt op termijn geen updates meer).

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

Vul in:
- `TORBOX_EMAIL` en `TORBOX_API_KEY` (te vinden in je Torbox-account onder
  **Settings → Integrations**).
- `NORDVPN_OPENVPN_USER` / `NORDVPN_OPENVPN_PASSWORD` (NordVPN "Service
  credentials", zie hierboven) — **vereist**, anders starten prowlarr en
  decypharr nooit op.
- `PUID`/`PGID` moeten overeenkomen met de eigenaar van de `./library`-map op
  de host, anders kan de container niet schrijven (Readarr geeft dan een
  "Folder not writable"-fout bij het toevoegen van de root folder).

## Stap 3 — Eén script: `./install.sh`

```bash
./install.sh
```

Dit doet automatisch:
1. Controleert/installeert Docker en rclone.
2. Waarschuwt als NordVPN-credentials ontbreken (zie hierboven).
3. Maakt de Torbox rclone-remote (WebDAV) **non-interactief** aan met de
   gegevens uit `.env`.
4. Start de Dropbox rclone-configuratie — **interactief moment**: je krijgt
   een link, log in bij Dropbox en bevestig. (Geen browser op de Pi zelf?
   Draai op je laptop `rclone authorize dropbox` en plak het resultaat terug
   wanneer het script erom vraagt.)
5. Zet systemd-units klaar en start de Torbox-mount + de Dropbox-sync-timer
   (elke 30 minuten).
6. Start Readarr (Bookshelf) + Prowlarr + Decypharr + gluetun via Docker
   Compose.
7. **Pauzeert voor de Decypharr-wizard** (zie hierboven) — eenmalig,
   interactief, kan niet gescript worden.
8. Wacht tot Readarr/Prowlarr hun API-key gegenereerd hebben en configureert
   dan automatisch, via hun REST API's:
   - Decypharr's `config.json` patchen (ebook-bestandstypen + download-actie)
   - Prowlarr's Application URL op de gluetun-sidecar zetten
   - root folder `/books` in Readarr
   - Decypharr als qBittorrent-compatibele downloadclient in Readarr
   - de app-koppeling Prowlarr → Readarr (voor indexer-sync)

## Stap 4 — Openen

```
http://<tailscale-ip-van-pi>:8787   (Readarr / Bookshelf)
http://<tailscale-ip-van-pi>:9696   (Prowlarr, via gluetun)
http://<tailscale-ip-van-pi>:8282   (Decypharr, via gluetun)
```

## Wat jij nog moet doen (kan echt niet geautomatiseerd worden)

- **NordVPN "Service credentials" ophalen** en in `.env` zetten (eenmalig,
  vóór `install.sh`).
- **Dropbox-login** tijdens `install.sh` (interactieve OAuth, eenmalig).
- **Decypharr-setup-wizard** tijdens `install.sh` (Torbox API-key invullen,
  mount type "None" kiezen, eenmalig).
- **Indexers toevoegen in Prowlarr** (Settings → Indexers): dit zijn jouw
  eigen trackeraccounts (bv. MyAnonamouse of andere boeken-indexers), dat kan
  alleen jij invullen. Prowlarr pusht ze daarna automatisch door naar Readarr
  dankzij de app-koppeling die `install.sh` al heeft gelegd.
- **Metadataprofiel-taal** (Readarr → Settings → Metadata Profiles →
  Standard → Allowed Languages): staat standaard op Engels (`eng`). Wil je
  liever een andere taal, gebruik dan de ISO 639-2/B-code (bv. `nld` voor
  Nederlands, niet `nl` of `dut`) plus `null` (voor boeken zonder
  taalmetadata), anders wordt alles geweigerd.

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
container om) eenvoudiger en robuuster — dan hoef je dit niet te doen. Let
op: dit is niet getest en vereist dat `rclone` beschikbaar is *binnen* de
Readarr-container, wat bij het Bookshelf-image niet gegarandeerd is.

## Logs & troubleshooting

- Dropbox-sync log: `logs/dropbox-sync.log`
- Torbox-mount status: `systemctl status rclone-torbox-mount.service`
- Readarr/Prowlarr/Decypharr/gluetun-logs:
  `docker compose logs -f readarr prowlarr decypharr gluetun`
- App-koppeling opnieuw proberen: `./scripts/configure-apps.sh`
- Containers crashen direct (exit code 159, lege logs): zie het
  libseccomp2/Bullseye-probleem hierboven.
- "Folder '/books' is not writable": `PUID`/`PGID` in `.env` komt niet
  overeen met de eigenaar van `./library` op de host.
- **`prowlarr`/`decypharr` komen niet op, `docker compose ps` toont ze niet
  als running**: check `docker compose logs gluetun` — vrijwel altijd
  ontbrekende/foute NordVPN-credentials in `.env`.
- **Download blijft hangen op "downloading" of geeft
  `"no valid download links available"`**: Decypharr's `config.json` mist de
  ebook-fix. Draai `./scripts/configure-apps.sh` opnieuw, of handmatig:
  `allowed_file_types` moet `epub`/`mobi`/`pdf`/etc. bevatten en
  `default_download_action` moet `"download"` zijn (niet `"symlink"`, want we
  gebruiken mount type "None"). Herstart daarna `decypharr`.
- **Import faalt met "path does not exist"**: Readarr en Decypharr moeten
  hetzelfde downloadpad zien. Controleer dat
  `./config/decypharr/downloads:/app/downloads` in béide services staat in
  `docker-compose.yml`.
- **Indexer-test faalt met "Name does not resolve (prowlarr:9696)"**:
  Prowlarr's Application URL staat nog op de oude waarde. Draai
  `./scripts/configure-apps.sh` opnieuw (zet 'm automatisch op
  `http://gluetun:9696`), en check daarna of bestaande indexers in Readarr
  (Settings → Indexers) ook `http://gluetun:9696/...` als URL hebben —
  zo niet, verwijder en voeg opnieuw toe via Prowlarr's "Sync App Indexers".
