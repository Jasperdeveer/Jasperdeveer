# Shelfarr op de Raspberry Pi

[Shelfarr](https://shelfarr.org) is een self-hosted zoek- en downloadsysteem voor
e-books en audioboeken — Jellyseerr, maar dan voor boeken. Deze map bevat een
kant-en-klare Compose-stack, afgestemd op de Pi zoals die er nu bij staat:
Prowlarr als indexer-manager, Torbox als cloud-downloadclient via een rclone-mount
op `/mnt/torbox`, en een Dropbox-timer die de bibliotheek wegschrijft.

| Bestand | Waarvoor |
|---|---|
| `docker-compose.yml` | De stack. Shelfarr draait standaard; extra's zitten achter profiles. |
| `docker-compose.arr-network.yml` | Override om Shelfarr in het Docker-netwerk van Prowlarr te hangen. |
| `.env.example` | Alle paden en instellingen. Kopiëren naar `.env`. |
| `scripts/tailscale-serve.sh` | Zet de web-UI achter HTTPS op je tailnet. |

## Hoe dit in je stack past

Shelfarr neemt de rol van Readarr over: zoeken, aanvragen, release kiezen,
importeren. **Prowlarr, Torbox, rclone en de Dropbox-timer blijven ongewijzigd.**

```
   Shelfarr (:5056) ─┬─→ Prowlarr (:9696) ──→ indexers
                     └─→ Torbox-shim ────────→ Torbox (cloud-download)
                                                    │ rclone
                                              /mnt/torbox
                                                    │ import (copy)
                                              bibliotheek ──→ Dropbox-timer
```

Dat is geen toeval: **Readarr is op 27 juni 2025 gearchiveerd**, omdat het volledig
leunde op de Goodreads-metadata-API die offline ging. Shelfarr haalt metadata bij
Open Library en Hardcover en heeft dat probleem niet. Je kunt beide prima een tijdje
naast elkaar draaien — let dan op de twee punten in [stap 6](#6-naast-readarr-draaien).

## Vereisten

- **Een 64-bit OS.** Check met `uname -m` — dat moet `aarch64` geven. Op 32-bit
  Raspberry Pi OS start Shelfarr niet: er is alleen `linux/amd64` en `linux/arm64`.
- **Pi 4 of 5 met minimaal 2 GB RAM.** Shelfarr is een Rails-app.
- **Docker met de compose-plugin.**
- **Een externe SSD of HDD** voor de database — op een SD-kaart is continu schrijven
  vragen om problemen.
- Prowlarr, de Torbox-shim en de rclone-mount draaien al.

## 1. Installeren

```bash
# op de Pi
git clone https://github.com/Jasperdeveer/Jasperdeveer.git
cd Jasperdeveer/shelfarr-stack

cp .env.example .env
nano .env                    # paden, PUID/PGID (`id -u` / `id -g`), tijdzone

sudo mkdir -p /mnt/ssd/shelfarr/data /mnt/ssd/media/{audiobooks,ebooks}
sudo chown -R "$(id -u):$(id -g)" /mnt/ssd/shelfarr /mnt/ssd/media

docker compose up -d
docker compose logs -f shelfarr
```

De eerste start duurt op een Pi een minuut of twee. Ga daarna naar
`http://100.120.136.112:5056` — **de eerste account die je registreert wordt admin**,
dus doe dat meteen zelf.

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

*Admin → Settings → Indexer*: provider `prowlarr`, URL `http://100.120.136.112:9696`,
en de API-key uit *Prowlarr → Settings → General*.

> **Val waar iedereen in trapt:** `http://localhost:9696` werkt niet. `localhost` is
> binnen de Shelfarr-*container*, niet je Pi.

Wil je liever containernamen (`http://prowlarr:9696`) dan hang je Shelfarr in het
netwerk van Prowlarr:

```bash
docker inspect prowlarr -f '{{range $n,$_ := .NetworkSettings.Networks}}{{$n}}{{"\n"}}{{end}}'
# zet de gevonden naam als ARR_NETWORK in .env
docker compose -f docker-compose.yml -f docker-compose.arr-network.yml up -d
```

## 4. Torbox koppelen

Shelfarr praat niet rechtstreeks met Torbox — net als Readarr gaat het via de
qBittorrent-compatibele shim die je al draait. Kijk in **Readarr → Settings →
Download Clients** welk type en welke poort daar staan, en neem dat over in
**Shelfarr → Admin → Download Clients**:

| Wat er in Readarr staat | Type in Shelfarr |
|---|---|
| Decypharr (qBittorrent, meestal poort 8282) | `decypharr` |
| TorBoxarr / CatBox / rdt-client (qBittorrent-shim) | `qbittorrent` |
| Een echte qBittorrent of SABnzbd | `qbittorrent` / `sabnzbd` |

Vul dezelfde host, poort en inloggegevens in, met `http://100.120.136.112:<poort>` als
URL. Draai je nog geen shim, dan is [Decypharr](https://docs.decypharr.com/guides/debrid/torbox/)
de logische keuze: Shelfarr ondersteunt dat type native.

Geef Shelfarr wel een **eigen category** (bijvoorbeeld `shelfarr-books`), anders gaan
Readarr en Shelfarr elkaars downloads opeisen.

### De rclone-mount

Shelfarr leest de afgeronde bestanden uit `/mnt/torbox`, dat in de container als
`/downloads` verschijnt. Drie dingen moeten kloppen:

1. **Mount-propagation.** Een FUSE-mount die ná Docker wordt aangekoppeld is binnen
   een container onzichtbaar, tenzij de bind-mount `rslave` gebruikt. Dat staat al
   goed in `docker-compose.yml` (`ro,rslave`). Zonder dat zie je een lege map — dit
   is verreweg de meest voorkomende oorzaak van "hij importeert niks".
2. **`--allow-other`.** rclone moet met die vlag draaien, en `user_allow_other` moet
   aanstaan in `/etc/fuse.conf`. Anders kan alleen de rclone-gebruiker bij de mount en
   kijkt de container tegen `Permission denied` aan. Zet `--uid`/`--gid` gelijk aan je
   `PUID`/`PGID`.
3. **Directory-cache.** rclone cachet mapinhoud standaard 5 minuten, dus een net
   afgeronde download is er "nog niet" als Shelfarr gaat importeren. Draai de mount
   met `--dir-cache-time 1m --poll-interval 15s`.

Controleren of het werkt:

```bash
docker compose exec shelfarr ls /downloads
```

Zie je hier je Torbox-bestanden, dan is dit deel klaar.

## 5. Configuratie-checklist in de UI

1. *Admin → Settings → Indexer* — Prowlarr (stap 3).
2. *Admin → Download Clients* — je Torbox-shim, met eigen category (stap 4). Klik `Test`.
3. *Admin → Settings → Downloads → Output Paths*:
   - audioboeken `/audiobooks`, e-books `/ebooks`
   - **import-modus: `copy`.** `hardlink` kán niet — de rclone-mount en je SSD zijn
     verschillende filesystems. `move` wil je niet: dat probeert te verwijderen uit je
     Torbox-opslag (en mislukt sowieso op een read-only mount).
   - Houd er rekening mee dat `copy` betekent dat de Pi de bytes echt via rclone bij
     Torbox ophaalt. Een audioboek van een gigabyte duurt dus even.
4. *Admin → Settings → Language* — `enabled_languages` op `en` én `nl` als je ook
   Nederlandse boeken zoekt.
5. Optioneel: `auto_select_enabled` aan met `auto_select_min_seeders` en een
   `auto_select_confidence_threshold` van ~90, dan hoef je niet elke release zelf te kiezen.

Alle instellingen met hun defaults staan in de
[settings reference](https://shelfarr.org/configuration.html).

## 6. Naast Readarr draaien

Twee dingen om te regelen zolang beide draaien:

- **Aparte download-category** per app (stap 4), anders pikt de één de downloads van
  de ander op.
- **Aparte doelmappen.** Laat Shelfarr niet in Readarr's root folder schrijven —
  Readarr hernoemt en verplaatst daar bestanden, en dan raken beide het spoor bijster.
  Geef Shelfarr eigen submappen binnen de map die je Dropbox-timer synct; dan lopen
  nieuwe boeken vanzelf mee naar Dropbox.

Ben je tevreden over Shelfarr, dan kan Readarr uit — de metadata-bron waar het op
draaide bestaat niet meer, dus veel toekomst heeft het niet.

## 7. Optionele onderdelen

Standaard uit; op een Pi scheelt dat geheugen.

| Profile | Wat het doet | Commando |
|---|---|---|
| `audiobookshelf` | Luister/lees-app op `:13378`, in Shelfarr `http://audiobookshelf` | `docker compose --profile audiobookshelf up -d` |
| `flaresolverr` | Cloudflare-bypass, alleen nodig voor Anna's Archive | `docker compose --profile flaresolverr up -d` |
| `audible` | Libation-companion voor Audible-backups (beta) | `docker compose --profile audible up -d` |

Permanent aanzetten kan met `COMPOSE_PROFILES=audiobookshelf` in je `.env`.

FlareSolverr draait een echte browser tegen externe pagina's. Zet je het aan, beperk
dan het uitgaande verkeer van die container (geen toegang tot je LAN, loopback of
link-local) — Shelfarr kan niet controleren wat er binnen FlareSolverr wordt opgehaald.

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
| `/downloads` is leeg in de container | Mount-propagation of `--allow-other` (stap 4). Check met `docker compose exec shelfarr ls /downloads`. |
| Download slaagt, import gebeurt nooit | rclone's dir-cache: het bestand is nog niet zichtbaar. `--dir-cache-time 1m --poll-interval 15s`. |
| `Permission denied` op `/downloads` | rclone's `--uid`/`--gid` komen niet overeen met `PUID`/`PGID` in `.env`. |
| Import faalt op hardlink | Zet de import-modus op `copy` — cross-filesystem hardlinks bestaan niet. |
| `exec format error` bij het starten | 32-bit OS. `uname -m` moet `aarch64` geven. |
| `Permission denied` op de bibliotheekmappen | `PUID`/`PGID` komen niet overeen met de eigenaar. Check `id -u`, `id -g`, `ls -ln /mnt/ssd/media`. |
| Klacht over eigenaarschap bij het starten | Zet `CHOWN_ON_START=never` in `.env`. |
| Container blijft `unhealthy` na de eerste start | De healthcheck heeft 90s speling; kijk in `docker compose logs shelfarr` of hij echt vastloopt. |
| Prowlarr- of download client-test faalt | `localhost` gebruikt. Neem `http://100.120.136.112:<poort>`. |
| Readarr en Shelfarr pakken elkaars downloads | Aparte category per app (stap 6). |
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
- [Readarr (Retired) — Servarr Wiki](https://wiki.servarr.com/readarr)
