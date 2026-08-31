# Shelfarr op de Raspberry Pi

[Shelfarr](https://shelfarr.org) is een self-hosted zoek- en downloadsysteem voor
e-books en audioboeken — Jellyseerr, maar dan voor boeken. Deze map bevat een
kant-en-klare Compose-stack, afgestemd op de Pi zoals die er nu bij staat:
Prowlarr als indexer-manager, Torbox als cloud-downloadclient via een rclone-mount
op `/mnt/torbox`, en een Dropbox-timer die de bibliotheek wegschrijft.

| Bestand | Waarvoor |
|---|---|
| `docker-compose.yml` | De stack. Shelfarr draait standaard; extra's zitten achter profiles. |
| `docker-compose.arr-network.yml` | Override om Shelfarr in het Docker-netwerk van gluetun te hangen. |
| `docker-compose.symlinks.yml` | Override die de rclone-mount óók op zijn eigen pad aankoppelt. |
| `docker-compose.compat.yml` | Override voor een 32-bit Docker-daemon die arm64-containers draait. |
| `scripts/make-env.sh` | Leest de draaiende stack uit en schrijft daaruit `.env`. |
| `scripts/configure-shelfarr.sh` | Zet indexer, download client en output paths, zonder de UI. |
| `.env.example` | Alle paden en instellingen. Kopiëren naar `.env`. |
| `scripts/stack-check.sh` | Leest je bestaande stack uit en zegt wat er in `.env` moet. |
| `CLAUDE.md` | Context voor een Claude Code-sessie die op de Pi zelf draait. |
| `scripts/tailscale-serve.sh` | Zet de web-UI achter HTTPS op je tailnet. |

## Hoe dit in je stack past

Shelfarr doet hetzelfde werk als je Bookshelf: zoeken, release kiezen, importeren.
**Prowlarr, gluetun, Decypharr, Torbox, rclone en de Dropbox-timer blijven
ongewijzigd** — Shelfarr komt ernaast te staan.

```
   Shelfarr (:5056) ─┬─→ Prowlarr (gluetun:9696) ──→ indexers
                     └─→ Decypharr (gluetun:8282) ─→ Torbox (cloud-download)
                                                          │ rclone
                                                    /mnt/torbox
                                                          │ import (copy)
                                                    bibliotheek ──→ Dropbox-timer
```

Je draait [Bookshelf](https://github.com/pennydreadful/bookshelf), een actief
onderhouden Readarr-revival met Hardcover-metadata — niet het originele Readarr, dat
op 27 juni 2025 werd gearchiveerd toen de Goodreads-API verdween. Je zit dus niet op
doodlopende software, en Shelfarr is hier een *alternatief*, geen redding.

Waar ze van elkaar verschillen: Bookshelf monitort auteurs en RSS-feeds en houdt een
bibliotheek bij. Shelfarr is een aanvraagsysteem in Jellyseerr-stijl met meerdere
gebruikers, en kan naast indexers ook directe bronnen aanspreken (Anna's Archive,
Z-Library, LibriVox) plus Audiobookshelf aansturen. De download-kant overlapt volledig.
Naast elkaar draaien kan prima; let op de punten in
[stap 6](#6-naast-bookshelf-draaien).

## Deze Pi: 64-bit kernel, 32-bit userland

Deze Pi draait een 64-bit kernel met een 32-bit (`armhf`) userland — een veel
voorkomende combinatie op Raspberry Pi OS. `uname -m` meldt daardoor `aarch64`
terwijl `dpkg --print-architecture` `armhf` zegt. Gevolg:

```bash
uname -m                                     # aarch64  — de kernel
dpkg --print-architecture                    # armhf    — de userland
docker version --format '{{.Server.Arch}}'   # arm      — wat Docker standaard pullt
```

Docker zou dus `linux/arm/v7`-images ophalen, en die bestaan niet voor Shelfarr.
Omdat de kernel wél 64-bit is, kunnen arm64-**containers** gewoon draaien: die
brengen hun eigen 64-bit userland mee. Daarom staat in `docker-compose.yml` bij elke
service een expliciete `platform: linux/arm64`.

Controleer eerst of dat op jouw Pi werkt:

```bash
docker run --rm --platform linux/arm64 arm64v8/alpine uname -m
```

- Antwoordt dit `aarch64`, dan draaien arm64-containers en kun je gewoon verder.
- Faalt het met `exec format error`, dan kan deze Pi geen 64-bit containers draaien
  en is een herinstallatie met 64-bit Raspberry Pi OS de enige route.

Er is nog een tweede gevolg. Een 32-bit daemon bouwt het seccomp-filter voor de
arm32-syscalltabel, en de aarch64-syscalls van de container matchen daar niet mee:
het proces wordt gedood met SIGSYS en de container herstart eindeloos met
`exited with code 159` (128 + 31). `docker-compose.compat.yml` zet dat filter uit
voor deze twee containers; `make-env.sh` schakelt die override automatisch in zodra
het een 32-bit daemon ziet. Het kost een laag isolatie, en verdwijnt zodra je een
64-bit userland draait.

Wat hier níét mee opgelost wordt, is software die je rechtstreeks op de Pi
installeert. Claude Code publiceert alleen x64- en arm64-binaries, en die starten
niet op een 32-bit userland: je krijgt `No such file or directory` op een bestand dat
er wel degelijk staat — dat is de ontbrekende 64-bit linker. Daarvoor is een 64-bit
OS nodig.

## Dit vanaf de Pi zelf afmaken

Dit werkt alleen op een 64-bit userland (zie hierboven) met 4 GB RAM of meer. Is dat
het geval, dan hoef je de configuratie niet met de hand na te rekenen:

```bash
cd ~/Jasperdeveer && git fetch origin
git checkout claude/shelfarr-stack-integration-c4z6ki

curl -fsSL https://claude.ai/install.sh | bash
cd shelfarr-stack && claude
```

`CLAUDE.md` in deze map bevat de volledige context van je stack en wat er nog
uitgezocht moet worden, dus die sessie begint niet blanco.

## Vereisten

- **Een 64-bit kernel.** `uname -m` moet `aarch64` geven. De userland mag 32-bit
  zijn — zie hieronder — maar de kernel niet.
- **Pi 4 of 5 met minimaal 2 GB RAM.** Shelfarr is een Rails-app.
- **Docker met de compose-plugin.**
- **Bij voorkeur een externe SSD of HDD.** Deze Pi heeft die niet: `/mnt/torbox` is de
  enige mount, en zowel de bibliotheek als Shelfarr's database staan op de SD-kaart.
  Dat werkt, maar houd twee dingen in de gaten. De SQLite-database schrijft continu,
  wat SD-kaarten op termijn sloopt. En omdat er met `copy` wordt geïmporteerd, komen
  alle boeken écht op die kaart te staan — een handvol audioboeken is zo een paar
  gigabyte. Check `df -h /` af en toe, en verhuis `DATA_PATH` en de bibliotheek naar
  externe opslag zodra je die aansluit.
- Prowlarr en Decypharr draaien al, allebei in gluetun's netwerk-namespace, en de
  rclone-mount op `/mnt/torbox` staat.

## 1. Installeren

```bash
cd ~/Jasperdeveer && git pull
cd shelfarr-stack

./scripts/make-env.sh --dry-run     # kijken wat het afleidt
./scripts/make-env.sh               # .env schrijven
```

`make-env.sh` leest gluetun's netwerknaam, de rclone-mount, Decypharr's downloadmap en
je PUID/PGID en tijdzone rechtstreeks uit het draaiende systeem, en zet meteen de juiste
`COMPOSE_FILE` — inclusief `docker-compose.symlinks.yml` als Decypharr symlinks buiten de
mount neerzet die naar bestanden erbinnen wijzen.

Wat het **niet** kan weten, is waar je boeken heen moeten. Controleer die twee regels:

```bash
grep -E 'AUDIOBOOKS_PATH|EBOOKS_PATH' .env
```

Ze moeten binnen de map liggen die je Dropbox-timer synct, en buiten de root folder van
Bookshelf. Klopt het niet, pas het aan. Daarna:

```bash
mkdir -p "$(grep ^AUDIOBOOKS_PATH .env | cut -d= -f2)" "$(grep ^EBOOKS_PATH .env | cut -d= -f2)"
docker compose up -d
docker compose logs -f shelfarr
```

De eerste start duurt op een Pi een minuut of twee. Ga daarna naar
`http://100.120.136.112:5056` — **de eerste account die je registreert wordt admin**,
dus doe dat meteen zelf.

Controleer voor je verder gaat of de container de mount en Decypharr ziet:

```bash
docker compose exec shelfarr ls /mnt/torbox | head
docker compose exec shelfarr wget -qO- http://gluetun:8282 >/dev/null && echo decypharr-bereikbaar
```

## 2. Toegang via Tailscale

**Aanrader — HTTPS op je tailnet:**

```bash
./scripts/tailscale-serve.sh
```

Shelfarr staat dan op `https://<machine>.<tailnet>.ts.net` met een geldig certificaat.
Zet daarna `BIND_ADDRESS=127.0.0.1` in `.env` en draai `docker compose up -d`, dan is
poort 5056 niet meer los benaderbaar op je LAN.

**Simpeler:** laat `BIND_ADDRESS=0.0.0.0` staan en gebruik `http://100.120.136.112:5056`.

> Gebruik **geen** `tailscale funnel` — dat publiceert Shelfarr op het open internet.

## 3. Prowlarr koppelen

Prowlarr deelt gluetun's netwerk-namespace en heet daarbinnen dus ook `gluetun`.
Shelfarr hangt in hetzelfde Docker-netwerk (dat regelt `docker-compose.arr-network.yml`):

*Admin → Settings → Indexer*: provider `prowlarr`, URL `http://gluetun:9696`, en de
API-key uit *Prowlarr → Settings → General*.

gluetun publiceert 9696 ook op de host, dus `http://100.120.136.112:9696` werkt net zo
goed als je de override liever niet gebruikt.

> **Val waar iedereen in trapt:** `http://localhost:9696` werkt niet. `localhost` is
> binnen de Shelfarr-*container*, niet je Pi.

## 4. Decypharr (Torbox) koppelen

Shelfarr praat niet rechtstreeks met Torbox — het gebruikt dezelfde Decypharr als
Bookshelf. Shelfarr ondersteunt dat type native, dus neem in **Admin → Download
Clients** over wat er in Bookshelf staat:

| Veld | Waarde |
|---|---|
| Type | `decypharr` |
| URL | `http://gluetun:8282` |
| Username / Password | dezelfde als in Bookshelf — zie hieronder |
| Category | `shelfarr` — Bookshelf gebruikt `readarr`, dus **niet** die |

Decypharr draait in gluetun's netwerk-namespace en heeft daardoor geen eigen hostnaam;
`gluetun` ís het adres. gluetun publiceert 8282 ook op de host, dus
`http://100.120.136.112:8282` werkt eveneens.

Decypharr staat op authenticatie (`use_auth: true`), dus je hebt de inloggegevens nodig.
Bookshelf toont het wachtwoord niet — haal het uit Decypharr's eigen config op
`~/Jasperdeveer/readarr-raspberrypi-setup/config/decypharr/config.json`, of uit zijn web-UI.

Die eigen category is belangrijk: staat Shelfarr ook op `readarr`, dan gaan beide apps
elkaars downloads opeisen.

Bookshelf heeft geen Remote Path Mappings ingevuld staan — Decypharr en Bookshelf zien
de bestanden dus op precies hetzelfde pad. Dat moet voor Shelfarr net zo blijven; daar
gaat de volgende paragraaf over.

### De rclone-mount en Decypharr's symlinks

Decypharr downloadt niets naar de Pi. Het zet **symlinks** neer die wijzen naar de
rclone-mount, en Shelfarr volgt die symlinks bij het importeren. Daarom staan host- en
containerpad in `docker-compose.yml` op precies hetzelfde: een symlink naar
`/mnt/torbox/...` breekt zodra de container dat bestand op `/downloads/...` ziet.

Staan Decypharr's symlinks in een aparte map (bijvoorbeeld `/mnt/symlinks`), zet dan
`DOWNLOADS_PATH` én `DOWNLOADS_CONTAINER_PATH` op de gedeelde bovenliggende map `/mnt`.
Welke map het is zegt `./scripts/stack-check.sh` je — die laat zien waar de symlinks
staan en waar ze heen wijzen. Anders staat het in Decypharr's config, of in Bookshelf →
Activity → History bij een geïmporteerd boek.

Aan de mount zelf hoeft niets te veranderen — die staat al goed:

```
rclone mount torbox: /mnt/torbox --allow-other --vfs-cache-mode=full --dir-cache-time=1m
```

- `--allow-other` staat aan, dus containers kunnen erbij (`user_id=1000,group_id=1000`
  komt overeen met `PUID`/`PGID`).
- `--dir-cache-time=1m` is kort genoeg dat een net afgeronde download snel zichtbaar is.
  Zonder dat cachet rclone vijf minuten en faalt de import terwijl het bestand er "al" is.
- **Mount-propagation** is het enige wat aan Docker-kant nodig is: een FUSE-mount die ná
  Docker wordt aangekoppeld is onzichtbaar in een container, tenzij de bind-mount
  `rslave` gebruikt. Dat staat al zo in `docker-compose.yml`.

Controleren of alles klopt:

```bash
docker compose exec shelfarr ls /mnt/torbox        # ziet de container de mount?
docker compose exec shelfarr wget -qO- http://gluetun:8282 >/dev/null && echo decypharr-ok
```

## 5. Configureren

Nadat je je adminaccount hebt geregistreerd:

```bash
./scripts/configure-shelfarr.sh
```

Dat zet de indexer, de download client en de output paths in één keer. De
Prowlarr-API-key leest het uit de draaiende Prowlarr-container, en de
Decypharr-inloggegevens uit Bookshelf's eigen download client-instellingen — die
werken aantoonbaar, dus overtypen hoeft niet. Lukt dat niet, dan vraagt het script
erom. Aan het eind test het beide verbindingen en laat het zien hoeveel items de
container in `/audiobooks`, `/ebooks` en de downloadmount ziet.

Het zet ook **Project Gutenberg en LibriVox** aan. Die twee hebben geen account,
key of extra container nodig — alleen hun toggle en een standaard-URL — en leveren
gratis publiek domein: klassieke e-books en voorgelezen audioboeken.

Herhaald draaien is veilig: bestaande waarden worden bijgewerkt, niet gedupliceerd.

Twee dingen over Decypharr die verklaren waarom de ingevulde waarden er vreemd
uitzien. De username is niet een gewone login maar de **host van de arr**, met de
API-key van die arr als wachtwoord — dat is Decypharr's manier om te weten wie er
aanklopt. Het script neemt Bookshelf's paar over, dus Shelfarr meldt zich aan als
Bookshelf. Voor het downloadverkeer maakt dat niets uit, want Shelfarr pollt zelf
de qBittorrent-API; het telt alleen als Decypharr ooit terug wil bellen naar de arr.
En de **category bepaalt de submap** waarin Decypharr de bestanden zet, dus met
`shelfarr` staan die netjes los van wat Bookshelf binnenhaalt.

### Of met de hand, in de UI

1. *Admin → Settings → Indexer* — provider `prowlarr`, URL `http://gluetun:9696`,
   API-key uit *Prowlarr → Settings → General*.
2. *Admin → Download Clients* — type `decypharr`, URL `http://gluetun:8282`, de
   inloggegevens uit Decypharr, category `shelfarr`. Klik `Test`.
3. *Admin → Settings → Downloads → Output Paths*:
   - audioboeken `/audiobooks`, e-books `/ebooks`
   - `download_local_path` op de downloadmount, dus `/mnt/torbox`
   - **import-modus: `copy`.** `hardlink` kán niet — de rclone-mount en je SD-kaart
     zijn verschillende filesystems, en je importeert via een symlink. `move` wil je
     niet: dat probeert te verwijderen uit je Torbox-opslag.
   - Reken erop dat `copy` de bytes echt via rclone bij Torbox ophaalt. Een audioboek
     van een gigabyte duurt dus even, en landt op je SD-kaart.
4. *Admin → Settings → Language* — `enabled_languages` op `en` én `nl`.
5. Optioneel: `auto_select_enabled` aan met `auto_select_min_seeders` en een
   `auto_select_confidence_threshold` van ~90.

Alle instellingen met hun defaults staan in de
[settings reference](https://shelfarr.org/configuration.html).

## 6. Naast Bookshelf draaien

Twee dingen om te regelen zolang beide draaien:

- **Aparte download-category** per app: Bookshelf staat op `readarr`, geef Shelfarr
  `shelfarr`. Anders pikt de één de downloads van de ander op.
- **Aparte doelmappen.** Laat Shelfarr niet in Bookshelf's root folder schrijven —
  Bookshelf hernoemt en verplaatst daar bestanden, en dan raken beide het spoor bijster.
  Geef Shelfarr eigen submappen binnen de map die je Dropbox-timer synct; dan lopen
  nieuwe boeken vanzelf mee naar Dropbox.

Bookshelf wordt actief onderhouden, dus er is geen reden om het weg te doen. Bevalt
Shelfarr beter, dan kan het alsnog; bevalt Bookshelf beter, dan is deze stack in twee
commando's weer weg (`docker compose down` en de map verwijderen).

## 7. Optionele onderdelen

Standaard uit; op een Pi scheelt dat geheugen.

| Profile | Wat het doet | Commando |
|---|---|---|
| `audiobookshelf` | Luister/lees-app op `:13378`, in Shelfarr `http://audiobookshelf` | `docker compose --profile audiobookshelf up -d` |
| `flaresolverr` | Cloudflare-bypass, alleen nodig voor Anna's Archive | `docker compose --profile flaresolverr up -d` |
| `audible` | Libation-companion voor Audible-backups (beta) | `docker compose --profile audible up -d` |

Permanent aanzetten kan met `COMPOSE_PROFILES=audiobookshelf` in je `.env`.

### Betere zoekresultaten: Hardcover

Vindt Shelfarr zelfs bekende titels niet, dan ligt dat aan de **metadata**, niet aan je
indexers: de zoekbalk zoekt in Open Library en Hardcover, en pas ná het aanvragen gaat
Prowlarr op zoek naar een release.

Hardcover is de betere van de twee, maar `hardcover_configured?` eist een niet-lege
`hardcover_api_token` — zonder token draait alles op Open Library alleen, en dat mist
veel. Een token is gratis: maak een account op
[hardcover.app](https://hardcover.app/account/api) en kopieer het.

```bash
./scripts/configure-shelfarr.sh --with-hardcover
```

De standaardrun verhoogt sowieso de zoeklimieten van 20 naar 40 (Open Library) en van
10 naar 25 (Hardcover); de defaults zijn krap voor auteurs met veel titels of edities.

### FlareSolverr en Anna's Archive

```bash
./scripts/configure-shelfarr.sh --with-anna
```

Dat start FlareSolverr (zet `COMPOSE_PROFILES=flaresolverr` in je `.env`), wacht tot
hij antwoordt, zet `flaresolverr_url` en de Anna's Archive-toggle, en vraagt om de
API-key.

Die key is geen formaliteit: Shelfarr's `anna_archive_configured?` eist **zowel** de
toggle **als** een niet-lege `anna_archive_api_key`. Zonder member-key (die krijg je
via een donatie) blijft de bron ongebruikt, hoe je hem ook aanzet. Het script zegt aan
het eind welke van de twee het is.

Twee praktische dingen op een Pi. FlareSolverr draait een headless Chromium, dus reken
op een paar honderd MB extra geheugengebruik zodra er een pagina wordt opgehaald. En
het draait een echte browser tegen externe pagina's: Shelfarr kan niet controleren wat
daarbinnen wordt opgevraagd, dus je wilt die container niet bij je LAN laten. Een
concrete afscherming, met een eigen subnet en een regel in de `DOCKER-USER`-keten:

```bash
# geef flaresolverr een eigen subnet in docker-compose.override.yml, bijvoorbeeld
# 172.31.9.0/24, en blokkeer daarvandaan al het privéverkeer:
sudo iptables -I DOCKER-USER -s 172.31.9.0/24 -d 10.0.0.0/8     -j DROP
sudo iptables -I DOCKER-USER -s 172.31.9.0/24 -d 172.16.0.0/12  -j DROP
sudo iptables -I DOCKER-USER -s 172.31.9.0/24 -d 192.168.0.0/16 -j DROP
sudo iptables -I DOCKER-USER -s 172.31.9.0/24 -d 169.254.0.0/16 -j DROP
```

Bewaar die regels met `iptables-persistent`, anders zijn ze na een herstart weg.

## 8. Beheer

```bash
docker compose ps                              # status + health
docker compose logs -f shelfarr                # meekijken
docker compose pull && docker compose up -d    # updaten
docker image prune -f                          # oude images opruimen
```

**Updaten:** verhoog `SHELFARR_VERSION` in `.env` naar de nieuwste release van
[shelfarr/releases](https://github.com/Pedro-Revez-Silva/shelfarr/releases) — release
`vYYYY.MM.DD.N` vul je in als `YYYY.MM.DD.N`, zonder de `v`. Pinnen is verstandig:
met `latest` haalt een `pull` zomaar een breaking change binnen.

**Backup:** alles wat telt staat in `DATA_PATH` — de database én de automatisch
gegenereerde `RAILS_MASTER_KEY` waarmee opgeslagen wachtwoorden en API-keys versleuteld
zijn. Zonder die map ben je je configuratie kwijt.

```bash
docker compose stop shelfarr
sudo tar czf ~/shelfarr-backup-$(date +%F).tar.gz -C /mnt/ssd/shelfarr data
docker compose start shelfarr
```

## 9. Problemen oplossen

| Symptoom | Oorzaak / oplossing |
|---|---|
| De mount is leeg in de container | Mount-propagation of `--allow-other` (stap 4). Check met `docker compose exec shelfarr ls /mnt/torbox`. |
| Download client-test faalt op `gluetun:8282` | Shelfarr hangt niet in het juiste netwerk. Check `ARR_NETWORK` en of je met de override start. |
| Import faalt op een symlink die nergens heen wijst | Host- en containerpad verschillen. Zet `DOWNLOADS_PATH` en `DOWNLOADS_CONTAINER_PATH` gelijk (stap 4). |
| Download slaagt, import gebeurt nooit | rclone's dir-cache: het bestand is nog niet zichtbaar. `--dir-cache-time 1m --poll-interval 15s`. |
| `Permission denied` op de mount | rclone's `--uid`/`--gid` komen niet overeen met `PUID`/`PGID` in `.env`. |
| Import faalt op hardlink | Zet de import-modus op `copy` — cross-filesystem hardlinks bestaan niet. |
| `no matching manifest for linux/arm/v7` | Docker pullt armv7. `DOCKER_PLATFORM=linux/arm64` in `.env` — zie de sectie over de 32-bit userland. |
| `exited with code 159`, container blijft herstarten | SIGSYS: seccomp doodt de arm64-container onder een 32-bit daemon. Voeg `docker-compose.compat.yml` toe aan `COMPOSE_FILE` (of draai `make-env.sh --force`). |
| `exec format error` bij het starten | De kernel is 32-bit. `uname -m` moet `aarch64` geven; zo niet, dan is een 64-bit OS nodig. |
| `Permission denied` op de bibliotheekmappen | `PUID`/`PGID` komen niet overeen met de eigenaar. Check `id -u`, `id -g`, `ls -ln /mnt/ssd/media`. |
| Klacht over eigenaarschap bij het starten | Zet `CHOWN_ON_START=never` in `.env`. |
| Container blijft `unhealthy` na de eerste start | De healthcheck heeft 90s speling; kijk in `docker compose logs shelfarr` of hij echt vastloopt. |
| Prowlarr-test faalt | `localhost` gebruikt, of `prowlarr` als hostnaam. Prowlarr zit in gluetun's namespace: `http://gluetun:9696`. |
| Bookshelf en Shelfarr pakken elkaars downloads | Beide staan op dezelfde category. Bookshelf houdt `readarr`, Shelfarr krijgt `shelfarr`. |
| Login lukt niet achter een eigen reverse proxy | De proxy moet `X-Forwarded-Proto` doorgeven. `tailscale serve` doet dat vanzelf. |
| Shelfarr op een subpad (`/shelfarr`) | Zet `RAILS_RELATIVE_URL_ROOT=/shelfarr` in de environment van de service. |

## 10. API

Maak een token onder *Profile → API tokens* (begint met `shf_`):

```bash
curl -H "Authorization: Bearer shf_..." \
  "https://<machine>.<tailnet>.ts.net/api/v1/search?q=dune"
```

## Bronnen

- [Getting started](https://shelfarr.org/getting-started.html) · [Settings reference](https://shelfarr.org/configuration.html)
- [github.com/Pedro-Revez-Silva/shelfarr](https://github.com/Pedro-Revez-Silva/shelfarr) (GPL-3.0)
- [Decypharr — Torbox setup](https://docs.decypharr.com/guides/debrid/torbox/)
- [Bookshelf — Readarr-revival](https://github.com/pennydreadful/bookshelf) · [Readarr (Retired)](https://wiki.servarr.com/readarr)
