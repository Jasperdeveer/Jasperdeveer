# Stremio – Beeld & Geluid Schatkamer

Stremio addon voor [schatkamer.beeldengeluid.nl](https://schatkamer.beeldengeluid.nl) – het gratis online archief van het Nederlands Instituut voor Beeld en Geluid met 700.000+ Nederlandse radio- en tv-programma's (1920–2020).

## Functies

- Bladeren door het Schatkamer-archief
- Zoeken op trefwoord
- Video's direct afspelen via de gevonden streamlinks
- Automatische fallback naar de browser als geen directe stream gevonden wordt

## Installatie

### 1. Vereisten

- Node.js 18 of nieuwer
- Google Chrome of Chromium (Puppeteer downloadt dit automatisch)

### 2. Addon starten

```bash
cd stremio-schatkamer
npm install
npm start
```

De addon start op `http://127.0.0.1:7000`.

### 3. Toevoegen aan Stremio

1. Open Stremio
2. Ga naar **Addons** → zoekbalk bovenin
3. Typ: `http://127.0.0.1:7000/manifest.json`
4. Klik op **Installeren**

## Configuratie

| Variabele | Standaard | Omschrijving |
|-----------|-----------|--------------|
| `PORT`    | `7000`    | Poort waarop de addon draait |

## Technische details

De addon gebruikt Puppeteer (headless Chrome) om de Schatkamer-website te doorzoeken en videostreams te onderscheppen. Elke aanvraag opent een browservenster op de achtergrond, haalt de data op, en sluit het venster weer. Resultaten worden 10 minuten gecached.

### Streaming

De addon onderschept netwerkrequests voor `.m3u8` (HLS) en `.mp4` bestanden terwijl de pagina laadt. Als geen directe stream gevonden wordt, wordt een link naar de browserversie aangeboden.

## Licentie

MIT
