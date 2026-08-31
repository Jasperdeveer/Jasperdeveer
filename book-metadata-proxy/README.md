# book-metadata-proxy

Cloudflare Worker die rijkere boek-metadata levert aan **Readarr** en **Shelfarr**.
Eén Worker, twee oppervlakken:

| Pad | Voor | Nabootsing van |
|---|---|---|
| `/v1/*` | Readarr | `api.bookinfo.club` (het BookInfo-contract) |
| `/search.json`, `/works/*`, `/authors/*`, `/isbn/*` | Shelfarr | `openlibrary.org` |

De data komt uit drie bronnen die elkaar aanvullen:

- **Open Library** — de ruggengraat. Enige gratis bron met stabiele ID's én een
  volledige auteur → werken → edities structuur. Geen sleutel nodig.
- **Hardcover** — de kwaliteitslaag: betere beschrijvingen, actuele covers en
  echte serie-informatie mét positie. Vereist een gratis API-token.
- **Google Books** — vult gaten in beschrijving, uitgever, taal en paginacount.
  Werkt zonder sleutel, met sleutel heb je een hoger quotum.

## Waarom dit nodig is

Readarr's eigen metadata-server (`api.bookinfo.club`) haalde zijn data uit de
Goodreads-API, die dicht is. Shelfarr gebruikt Open Library, dat vaak dunne
beschrijvingen en geen serie-informatie heeft. Deze proxy zet er een laag
tussen die de gaten vult, zonder dat je in Readarr of Shelfarr zelf iets hoeft
te patchen.

## Deployen

```bash
cd book-metadata-proxy
npm install

# KV-namespace voor de auteur-index en de verrijkingscache
npx wrangler kv namespace create METADATA
# plak het teruggegeven id in wrangler.toml bij [[kv_namespaces]]

# Hardcover-token (optioneel maar sterk aangeraden)
npx wrangler secret put HARDCOVER_TOKEN     # van https://hardcover.app/account/api
npx wrangler secret put GOOGLE_BOOKS_KEY    # optioneel

npx wrangler deploy
```

Zet ook je `account_id` en je `CONTACT_EMAIL` in `wrangler.toml`. Dat adres komt
in de `User-Agent` van elke uitgaande call — Open Library vraagt daar expliciet
om en blokkeert anonieme clients.

Controleer daarna:

```bash
curl https://book-metadata-proxy.<jouw-subdomain>.workers.dev/health
```

## Readarr instellen

De metadata-URL zit **niet in de Readarr-UI** — het veld hoort bij de
development-config. Zetten doe je via de API:

```bash
curl -X PUT "http://<readarr>:8787/api/v1/config/development" \
  -H "X-Api-Key: <jouw-readarr-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"id":1,"metadataSource":"https://book-metadata-proxy.<jouw-subdomain>.workers.dev/v1"}'
```

Haal eerst de huidige config op met een `GET` op hetzelfde adres en stuur die
terug mét `metadataSource` erin — Readarr valideert het hele object. De `/v1`
op het eind is verplicht: Readarr plakt er `author/123` achter.

Herstart Readarr en refresh een auteur.

### ID's

Readarr wil integers. Die zijn hier het cijferdeel van de Open Library-sleutel:

| Open Library | Readarr-id |
|---|---|
| `OL34184A` (auteur) | `34184` |
| `OL45804W` (werk) | `45804` |
| `OL51048152M` (editie) | `51048152` |

De vertaling is stateless en omkeerbaar — geen ID-database nodig.

Boeken toevoegen doe je in het zoekveld met een prefix, die gaan rechtstreeks
door deze proxy:

```
author:34184
work:45804
edition:51048152
```

### Wat deze proxy níet oplost

Het vrije zoekveld van Readarr gaat **niet** via de metadata-URL. `SearchForNewBook`
zonder prefix roept `GoodreadsSearchProxy` aan, en die heeft
`https://www.goodreads.com` hard in de code staan met een ingebakken sleutel.
Dat is niet configureerbaar. Zoeken op titel blijft dus afhankelijk van
Goodreads; alles daarna (auteur ophalen, boeken verversen, edities, series)
loopt wel via deze proxy. Gebruik de `author:` / `work:` / `edition:`-prefixes
om dat te omzeilen.

Readarr zelf is trouwens gearchiveerd. Als je toch aan het migreren bent, is
Shelfarr de actievere weg.

## Shelfarr instellen

Shelfarr heeft `openlibrary.org` hard in de code staan; alleen de keuze tússen
Hardcover en Open Library is instelbaar, niet het adres. Je wijst Shelfarr dus
op DNS-niveau hierheen.

In `docker-compose.yml` van Shelfarr:

```yaml
services:
  shelfarr:
    extra_hosts:
      - "openlibrary.org:<ip-van-je-reverse-proxy>"
```

Laat die reverse proxy (Caddy, nginx, Traefik) TLS termineren voor
`openlibrary.org` met een eigen certificaat dat de container vertrouwt, en
forward naar de Worker. Zonder dat opzetje kun je de Worker nog steeds direct
bevragen onder `/openlibrary/...` — handig om te testen:

```bash
curl "https://<worker>/openlibrary/works/OL45804W.json"
```

Vul in Shelfarr los daarvan ook gewoon je **`hardcover_api_token`** in en zet
`metadata_source` op `auto`. Voor veel gevallen is dat al de grootste
kwaliteitswinst, zonder host-override.

## Endpoints

### Readarr (`/v1`)

| Endpoint | Doet |
|---|---|
| `GET /v1/author/{id}` | Auteur plus al hun werken, elk met minstens één editie |
| `GET /v1/author/changed?since={iso}` | Antwoordt `Limited: true` — er is geen wijzigingslog |
| `GET /v1/work/{id}` | Volledig werk: echte edities, ISBN's, uitgevers, formaten |
| `GET /v1/book/{id}` | 302 naar `/v1/work/{id}` van het bijbehorende werk |
| `POST /v1/book/bulk` | Body is een JSON-array met editie-id's (max 20 per call) |

### Shelfarr (Open Library-vorm)

| Endpoint | Doet |
|---|---|
| `GET /search.json?q=&limit=` | Open Library-zoekresultaat, met beschrijving en cover erbij |
| `GET /works/{OL...W}.json` | Werk met de beste beschrijving van de drie bronnen |
| `GET /authors/{OL...A}.json` | Auteur met opgeschoonde bio |
| `GET /authors/{OL...A}/works.json` | Ongewijzigd doorgegeven |
| `GET /isbn/{isbn}.json` | Editie, aangevuld met paginacount en cover |

Alles is ook bereikbaar onder `/openlibrary/...`.

## Hoe de verrijking werkt

Een auteur ophalen kost twee tot drie requests: de auteur zelf, plus de
Search-API met alle werken in één klap (inclusief ISBN's, uitgever, paginacount
en ratings). Per werk een extra call doen zou het subrequest-budget van een
Worker opblazen.

Hardcover en Google Books worden er daarna overheen gelegd:

- Bij `/v1/work/{id}` meteen, want dat is één boek.
- Bij `/v1/author/{id}` in de achtergrond (`waitUntil`), in blokjes van
  `ENRICH_BATCH_SIZE` werken, gesorteerd op populariteit. Het resultaat gaat in
  KV; de volgende refresh van Readarr pikt het op. Ook mislukte pogingen worden
  onthouden, zodat onvindbare boeken niet elke ronde opnieuw geprobeerd worden.

Verrijking blokkeert nooit een antwoord: valt Hardcover weg, dan krijg je
gewoon wat Open Library had.

## Instellingen

| Variabele | Waar | Standaard | Betekenis |
|---|---|---|---|
| `CONTACT_EMAIL` | `wrangler.toml` | — | Komt in de User-Agent; Open Library vraagt hierom |
| `MAX_AUTHOR_WORKS` | `wrangler.toml` | `500` | Max werken per auteur |
| `MAX_WORK_EDITIONS` | `wrangler.toml` | `40` | Max edities per werk |
| `ENRICH_BATCH_SIZE` | `wrangler.toml` | `20` | Werken per achtergrondronde |
| `HARDCOVER_TOKEN` | secret | — | Zonder token slaat Hardcover stil over |
| `GOOGLE_BOOKS_KEY` | secret | — | Optioneel, hoger quotum |

## Tests

```bash
npm test
```

De tests in `test/bookinfo-contract.test.js` bewaken eisen die rechtstreeks uit
Readarr's broncode komen: PascalCase-sleutels (Readarr deserialiseert
case-sensitive), integer-ID's, nooit-null lijstvelden, en de regel dat de
opgevraagde auteur de eerste contributor moet zijn — anders laat Readarr het
boek stilletjes vallen. Pas ze niet aan zonder die code erbij te pakken.

## Bekende beperkingen

- **Vrij zoeken in Readarr** loopt via Goodreads, niet hierlangs (zie boven).
- **Releasejaren** komen van Open Library en kloppen niet altijd: een enkele
  fout gecatalogiseerde editie trekt het jaar van het hele werk mee. Open
  Library rekent dat zelf net zo uit, dus dit is brondata, geen bug hier.
- **Geen wijzigingslog.** `/v1/author/changed` antwoordt `Limited: true`,
  waarna Readarr een volledige refresh doet. Dat is trager maar eerlijk.
- **`POST /v1/book/bulk`** verwerkt maximaal 20 editie-id's per call vanwege het
  subrequest-budget van een Worker.

## Licentie

MIT
