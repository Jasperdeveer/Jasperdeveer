# Readarr op je Raspberry Pi, met Torbox als downloadbron en sync naar Dropbox

Deze map bevat een kant-en-klare Docker Compose-stack + installatiescript om
Readarr op je Raspberry Pi te draaien, Torbox als downloadclient te gebruiken,
en de resulterende boeken automatisch naar Dropbox te syncen.

**Belangrijk:** deze Claude-sessie draait in een losse cloud-omgeving en heeft
geen netwerktoegang tot jouw Tailnet of Pi — ik kan dit dus niet vanaf hier
uitvoeren. Ik heb wel alles zo ver mogelijk geautomatiseerd: `install.sh` doet
nu vrijwel alles in één run (rclone installeren, remotes aanmaken, systemd-
services, containers starten, én Readarr/Prowlarr automatisch aan elkaar en
aan Torbox koppelen via hun API's). De **enige stap die ik niet voor je kan
doen** is de Dropbox-login, omdat die een interactieve OAuth-bevestiging met
jouw account vereist.

De Dropbox-doelmap staat al klaar: **`/Jasper de Veer/Readarr-Library`** (heb
ik zojuist voor je aangemaakt via de Dropbox-koppeling van deze sessie).

## Architectuur

```
Torbox (WebDAV)  --rclone mount-->  /mnt/torbox  --bind mount-->  Readarr (import)
Torbox (qBittorrent-compatible API) <-- Readarr (download client, start/monitor)
Readarr  --organiseert boeken naar--> ./library
./library  --rclone copy (timer)-->  Dropbox: /Jasper de Veer/Readarr-Library
Prowlarr --indexers--> Readarr (zoeken naar boeken; Torbox zoekt zelf niet)
```

Torbox is geen *indexer* (zoekbron) maar een *downloadclient*: het haalt de
torrents/nzb's op die Readarr via indexers vindt. Je hebt dus naast Torbox nog
gewoon indexers nodig (via Prowlarr) — en dat is ook het enige andere stukje
dat alleen jij kan invullen, omdat het om jouw eigen trackeraccounts gaat.

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
onder **Settings → Integrations**). `DROPBOX_REMOTE` staat al goed ingesteld
op de map die ik heb aangemaakt.

## Stap 3 — Eén script: `./install.sh`

```bash
./install.sh
```

Dit doet automatisch:
1. Controleert/installeert Docker en rclone.
2. Maakt de Torbox rclone-remote (WebDAV) **non-interactief** aan met de
   gegevens uit `.env`.
3. Start de Dropbox rclone-configuratie — **dit is het enige interactieve
   moment**: je krijgt een link, log in bij Dropbox en bevestig. (Geen browser
   op de Pi zelf? Draai op je laptop `rclone authorize dropbox` en plak het
   resultaat terug wanneer het script erom vraagt.)
4. Zet systemd-units klaar en start de Torbox-mount + de Dropbox-sync-timer
   (elke 30 minuten).
5. Start Readarr + Prowlarr via Docker Compose.
6. Wacht tot beide apps hun API-key gegenereerd hebben en configureert dan
   automatisch, via hun REST API's:
   - root folder `/books` in Readarr
   - Torbox als qBittorrent-compatibele downloadclient in Readarr
   - de app-koppeling Prowlarr → Readarr (voor indexer-sync)

Aan het eind print het script de URL's en wat er nog (echt alleen door jou)
gedaan moet worden.

## Stap 4 — Openen

```
http://<tailscale-ip-van-pi>:8787   (Readarr)
http://<tailscale-ip-van-pi>:9696   (Prowlarr)
```

## Wat jij nog moet doen (kan echt niet geautomatiseerd worden)

- **Dropbox-login** tijdens `install.sh` (interactieve OAuth, eenmalig).
- **Indexers toevoegen in Prowlarr** (Settings → Indexers): dit zijn jouw
  eigen trackeraccounts (bv. MyAnonamouse of andere boeken-indexers), dat kan
  alleen jij invullen. Prowlarr pusht ze daarna automatisch door naar Readarr
  dankzij de app-koppeling die `install.sh` al heeft gelegd.

Als de automatische Readarr/Prowlarr-koppeling (stap 6) om wat voor reden dan
ook niet lukt (bijvoorbeeld omdat Torbox zijn API-velden heeft aangepast),
kun je 'm los opnieuw draaien of handmatig corrigeren:

```bash
./scripts/configure-apps.sh
```

Of handmatig in Readarr onder **Settings → Download Clients → + →
qBittorrent**, met host `qbittorrent.torbox.app`, poort `443`, SSL aan, en je
Torbox API key als gebruikersnaam/wachtwoord (controleer de actuele waarden
in je Torbox-account, want deze kunnen wijzigen).

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
- Readarr/Prowlarr logs: `docker compose logs -f readarr prowlarr`
- App-koppeling opnieuw proberen: `./scripts/configure-apps.sh`
