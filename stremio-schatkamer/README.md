# Stremio – Beeld & Geluid Schatkamer

Stremio addon voor [schatkamer.beeldengeluid.nl](https://schatkamer.beeldengeluid.nl) – het gratis online archief van het Nederlands Instituut voor Beeld en Geluid met 700.000+ Nederlandse tv-programma's (1920–2020).

## Installeren in Stremio

Voeg deze URL toe in Stremio → Addons:

```
https://stremio-schatkamer.<jouw-subdomain>.workers.dev/manifest.json
```

## Deployen op Cloudflare Workers (gratis)

### 1. Vereisten

- [Cloudflare account](https://dash.cloudflare.com/sign-up) (gratis)
- Node.js 18+

### 2. Installeer Wrangler

```bash
npm install -g wrangler
wrangler login
```

### 3. Deploy

```bash
cd stremio-schatkamer
npm install
npm run deploy
```

Wrangler geeft na het deployen een URL terug zoals:
```
https://stremio-schatkamer.<jouw-account>.workers.dev
```

Voeg `/manifest.json` toe aan die URL en installeer hem in Stremio.

### Lokaal testen

```bash
npm run dev
# Addon draait op http://localhost:8787/manifest.json
```

## Hoe het werkt

De Worker haalt pagina's op van de Schatkamer met browser-achtige headers en parseert de HTML om:
- **Catalog**: zoekresultaten en browse-overzicht
- **Meta**: titel, poster, beschrijving per programma
- **Stream**: directe video-URL's (HLS/MP4) uit de videospeler-HTML

Resultaten worden gecached via de Cloudflare Cache API (10 min voor catalogs, 1 uur voor metadata).

## Licentie

MIT
