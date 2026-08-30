# Shelfarr op de Raspberry Pi

[Shelfarr](https://shelfarr.org) is een self-hosted zoek- en downloadsysteem voor
e-books en audioboeken — feitelijk Jellyseerr, maar dan voor boeken. Je zoekt een
boek, Shelfarr zoekt releases via je indexer, geeft ze aan je download client,
sorteert de bestanden in je bibliotheek en laat Audiobookshelf opnieuw scannen.

Deze map bevat een kant-en-klare Compose-stack, afgestemd op een Raspberry Pi met
toegang via Tailscale, en op een Prowlarr die al draait.

| Bestand | Waarvoor |
|---|---|
| `docker-compose.yml` | De stack. Shelfarr draait standaard; extra's zitten achter profiles. |
| `docker-compose.arr-network.yml` | Override om Shelfarr in het Docker-netwerk van je bestaande Prowlarr te hangen. |
| `.env.example` | Alle paden en instellingen. Kopiëren naar `.env`. |
| `scripts/tailscale-serve.sh` | Zet de web-UI achter HTTPS op je tailnet. |

## Vereisten

- **Een 64-bit OS.** Controleer met `uname -m` — dat moet `aarch64` teruggeven.
  Op 32-bit Raspberry Pi OS (`armv7l`) start Shelfarr niet: er is alleen een
  `linux/amd64`- en `linux/arm64`-image. Idem voor Audiobookshelf.
- **Pi 4 of 5 met minimaal 2 GB RAM.** Shelfarr is een Rails-app; op een Pi 3 of
  Zero is het geen pretje.
- **Docker met de compose-plugin**: `curl -fsSL https://get.docker.com | sh`, daarna
  `sudo usermod -aG docker $USER` en opnieuw inloggen.
- **Een externe SSD of HDD.** De database schrijft continu; op een SD-kaart is dat
  vragen om een kapotte kaart. Alle paden in `.env.example` wijzen daarom naar `/mnt/ssd`.
- **Prowlarr** (draait al) en **één download client** — een bestaande, of de
  qBittorrent die hier optioneel meekomt.

## 1. Installeren

```bash
# op de Pi
git clone https://github.com/Jasperdeveer/Jasperdeveer.git
cd Jasperdeveer/shelfarr-stack

cp .env.example .env
nano .env                    # paden, PUID/PGID (`id -u` / `id -g`) en tijdzone

# maak de mappen aan en zet ze op je eigen user
sudo mkdir -p /mnt/ssd/shelfarr/data /mnt/ssd/media/{audiobooks,ebooks} /mnt/ssd/downloads/complete
sudo chown -R "$(id -u):$(id -g)" /mnt/ssd/shelfarr /mnt/ssd/media /mnt/ssd/downloads

docker compose up -d
docker compose logs -f shelfarr
```

De eerste start duurt op een Pi een minuut of twee (database aanmaken, secret key
genereren). Ga daarna naar `http://<ip-van-je-pi>:5056` — **de eerste account die
je registreert wordt admin**, dus doe dat meteen zelf.

## 2. Toegang via Tailscale

**Aanrader — HTTPS op je tailnet:**

```bash
./scripts/tailscale-serve.sh
```

Dat zet Shelfarr op `https://<machine>.<tailnet>.ts.net` met een geldig certificaat.
Zet daarna `BIND_ADDRESS=127.0.0.1` in `.env` en draai `docker compose up -d`, dan is
poort 5056 niet meer los benaderbaar op je LAN — alles loopt via Tailscale.

**Simpeler, zonder proxy:** laat `BIND_ADDRESS=0.0.0.0` staan en ga naar
`http://<machine>:5056` via MagicDNS of het `100.x.y.z`-adres van je Pi.

> Gebruik **geen** `tailscale funnel`: dat publiceert Shelfarr op het open internet.
> `serve` blijft binnen je tailnet, dat is wat je wil.

## 3. Prowlarr koppelen

Twee manieren. **Optie A werkt altijd**, ook als Prowlarr los van deze stack draait:

**A — via het IP van je Pi.** In Shelfarr: *Admin → Settings → Indexer*,
provider `prowlarr`, URL `http://<ip-van-je-pi>:9696`, en de API-key uit
*Prowlarr → Settings → General*.

**B — via een gedeeld Docker-netwerk**, dan kun je gewoon `http://prowlarr:9696`
gebruiken:

```bash
docker inspect prowlarr -f '{{range $n,$_ := .NetworkSettings.Networks}}{{$n}}{{"\n"}}{{end}}'
# zet de gevonden naam als ARR_NETWORK in .env
docker compose -f docker-compose.yml -f docker-compose.arr-network.yml up -d
```

> **Val waar iedereen in trapt:** `http://localhost:9696` invullen werkt niet.
> `localhost` is binnen de Shelfarr-*container*, niet je Pi.

Zorg dat er in Prowlarr indexers staan die boeken voeren; Shelfarr filtert
desgewenst op tags via de instelling `prowlarr_tags`.

## 4. Download client

**Heb je er al één?** Voeg hem toe onder *Admin → Download Clients*: type, URL
(`http://<ip-van-je-pi>:8080` of de containernaam bij optie B hierboven), en een
category zoals `books`.

**Nog niet?** Start de meegeleverde qBittorrent:

```bash
docker compose --profile qbittorrent up -d
docker compose logs qbittorrent | grep -i password   # tijdelijk wachtwoord bij eerste start
```

Web-UI op poort `8081`, in Shelfarr bereikbaar als `http://qbittorrent:8081`. Zet in
qBittorrent het opslagpad op `/downloads`.

**Het belangrijkste detail:** de download client en Shelfarr moeten dezelfde map op
*hetzelfde containerpad* zien — beide `/downloads`. Dat is in deze compose zo
ingericht. Wijkt je bestaande client daarvan af, vul dan
*Output Paths → `download_remote_path` / `download_local_path`* in, anders vindt
Shelfarr de afgeronde bestanden niet.

Staan `DOWNLOADS_PATH` en je bibliotheken op hetzelfde filesystem, kies dan
import-modus **hardlink**: importeren is dan instant en kost geen extra schijfruimte
(relevant als je seedt).

## 5. Configuratie-checklist in de UI

1. *Admin → Settings → Indexer* — provider, URL, API-key. (Stap 3)
2. *Admin → Download Clients* — client toevoegen, `Test`. (Stap 4)
3. *Admin → Settings → Downloads → Output Paths* — `/audiobooks` en `/ebooks`,
   import-modus, en eventueel de naamsjablonen (`{author}/{title}` standaard).
4. *Admin → Settings → Language* — `enabled_languages` op `en` én `nl` als je ook
   Nederlandse boeken zoekt; `default_language` naar smaak.
5. Optioneel: *Library Platform* → Audiobookshelf-URL, API-token en de library-ID's.
6. Optioneel: *auto_select_enabled* aan met `auto_select_min_seeders` en een
   `auto_select_confidence_threshold` van ~90, dan hoef je niet elke release zelf te kiezen.

Alle instellingen met hun defaults staan in de
[settings reference](https://shelfarr.org/configuration.html).

## 6. Optionele onderdelen

Ze staan standaard uit — op een Pi scheelt dat geheugen. Aanzetten doe je per profile:

| Profile | Wat het doet | Commando |
|---|---|---|
| `qbittorrent` | Download client, web-UI op `:8081` | `docker compose --profile qbittorrent up -d` |
| `audiobookshelf` | Luister/lees-app op `:13378`, in Shelfarr `http://audiobookshelf` | `docker compose --profile audiobookshelf up -d` |
| `flaresolverr` | Cloudflare-bypass, alleen nodig voor Anna's Archive | `docker compose --profile flaresolverr up -d` |
| `audible` | Libation-companion voor Audible-backups (beta) | `docker compose --profile audible up -d` |

Combineren mag: `docker compose --profile qbittorrent --profile audiobookshelf up -d`.
Wil je ze permanent, zet dan `COMPOSE_PROFILES=qbittorrent,audiobookshelf` in je `.env`.

FlareSolverr draait een echte browser tegen externe pagina's. Zet je het aan, beperk
dan het uitgaande verkeer van die container (geen toegang tot je LAN, loopback of
link-local) — Shelfarr kan niet controleren wat er binnen FlareSolverr wordt opgehaald.

## 7. Beheer

```bash
docker compose ps                      # status + health
docker compose logs -f shelfarr        # meekijken
docker compose pull && docker compose up -d    # updaten
docker image prune -f                  # oude images opruimen
```

**Updaten:** verhoog `SHELFARR_VERSION` in `.env` naar de nieuwste release van
[shelfarr/releases](https://github.com/Pedro-Revez-Silva/shelfarr/releases) — een
release `vYYYY.MM.DD.N` vul je in als `YYYY.MM.DD.N`, zonder de `v`. Pinnen is
verstandig: met `latest` haalt een `pull` zomaar een breaking change binnen.

**Backup:** alles wat telt staat in `DATA_PATH` — de database én de automatisch
gegenereerde `RAILS_MASTER_KEY` waarmee je opgeslagen wachtwoorden en API-keys
versleuteld zijn. Zonder die map ben je je configuratie kwijt.

```bash
docker compose stop shelfarr
sudo tar czf ~/shelfarr-backup-$(date +%F).tar.gz -C /mnt/ssd/shelfarr data
docker compose start shelfarr
```

## 8. Problemen oplossen

| Symptoom | Oorzaak / oplossing |
|---|---|
| `exec format error` bij het starten | 32-bit OS. Check `uname -m`; dat moet `aarch64` zijn. |
| `Permission denied` op de bibliotheekmappen | `PUID`/`PGID` in `.env` komen niet overeen met de eigenaar van de mappen. Check `id -u`, `id -g` en `ls -ln /mnt/ssd/media`. |
| Container blijft `unhealthy` bij de eerste start | Op een Pi kan de eerste boot lang duren. De healthcheck heeft 90s speling; kijk in `docker compose logs shelfarr` of hij daadwerkelijk vastloopt. |
| Prowlarr-test faalt | `localhost` gebruikt in de URL. Gebruik het IP van je Pi of de containernaam (stap 3). |
| Download gaat weg maar wordt nooit geïmporteerd | Padmismatch: de client schrijft naar een ander pad dan Shelfarr in `/downloads` ziet. Zie stap 4. |
| Login lukt niet achter een eigen reverse proxy | De proxy moet `X-Forwarded-Proto` doorgeven, anders klopt Rails' origin-check niet. `tailscale serve` doet dit vanzelf. |
| Wil je Shelfarr op een subpad (`/shelfarr`) | Zet `RAILS_RELATIVE_URL_ROOT=/shelfarr` in de environment van de service. |
| Poort 5056 al bezet | Pas `SHELFARR_PORT` aan in `.env`. |

## 9. API

Maak een token onder *Profile → API tokens* (begint met `shf_`):

```bash
curl -H "Authorization: Bearer shf_..." \
  "https://<machine>.<tailnet>.ts.net/api/v1/search?q=dune"
```

## Bronnen

- [Getting started](https://shelfarr.org/getting-started.html) · [Settings reference](https://shelfarr.org/configuration.html)
- [github.com/Pedro-Revez-Silva/shelfarr](https://github.com/Pedro-Revez-Silva/shelfarr) (GPL-3.0)
