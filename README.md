# 🎨 Paint-by-Numbers Generator - Street Art Editie

Een professionele web applicatie voor het converteren van afbeeldingen naar paint-by-numbers sjablonen, speciaal ontworpen voor street art en spuitbus projecten.

## Features

### ✅ Kleurenpalet Beheer
- **Automatische kleurdetectie** met instelbaar maximum aantal kleuren (K-means clustering)
- **Kleuren toevoegen/verwijderen** met automatische herverdeling
- **Kleur hernoemen** functionaliteit
- **Undo functie** voor wijzigingen (tot 20 stappen)
- **Preview per kleur** (andere kleuren dimmen)

### ✅ Visualisatie Modes
Toggle tussen drie modes:
1. **Origineel** - Oorspronkelijke afbeelding
2. **Paint-by-Numbers** - Genummerde vlakken met contouren
3. **Lijntekening** - Alleen contouren (edge detection)

### ✅ Instelbare Parameters
- **Aantal kleuren** (2-32)
- **Cijfergrootte** (automatisch geschaald per vlakgrootte)
- **Lijndikte** voor contouren (1-10px)
- **Detailniveau** voor lijntekening (1-10)
- **Minimale vlakgrootte** (filtering kleine regio's)
- **Doekafmetingen** voor spuitbus berekening (in cm)

### ✅ Legenda met Spuitbus Berekening
- **Kleurnummers en namen**
- **Kleurvoorbeelden**
- **Oppervlakte percentages**
- **Benodigde aantal spuitbussen** per kleur
  - Gebaseerd op Montana Black dekking (~2-2.5m² per bus)
  - Automatische berekening op basis van doekafmetingen

### ✅ Extra Features
- **Zoom functionaliteit** (10%-500%)
- **SVG export** (vector formaat)
- **PNG export** (raster formaat)
- **Gebruiksvriendelijke interface** met moderne styling
- **Responsive design**

## Gebruik

1. Open `index.html` in een moderne browser
2. Upload een afbeelding via de file picker
3. Klik op "Detecteer Kleuren" om automatisch kleuren te detecteren
4. Pas parameters aan naar wens
5. Schakel tussen visualisatie modes
6. Bekijk de legenda voor spuitbus berekeningen
7. Export je sjabloon als SVG of PNG

## Technologie

- **Vanilla JavaScript** (ES6+)
- **HTML5 Canvas API** voor beeldverwerking
- **K-means clustering** voor kleurdetectie
- **Sobel edge detection** voor lijntekeningen
- **Flood fill algoritme** voor regio detectie
- **SVG generation** voor vector export

## Algoritmes

### Kleurdetectie
Gebruikt K-means clustering om de meest dominante kleuren in een afbeelding te identificeren. Het algoritme:
1. Neemt willekeurige pixels als sample (voor performance)
2. Initialiseert centroids
3. Itereert tot convergentie
4. Genereert automatisch kleurnamen

### Edge Detection
Sobel operator voor het detecteren van randen in de afbeelding, met instelbare threshold voor detailniveau.

### Regio Detectie
Flood fill algoritme om samenhangende kleurgebieden te vinden en hun zwaartepunten te berekenen voor optimale nummer plaatsing.

## Spuitbus Berekeningen

De applicatie berekent automatisch hoeveel spuitbussen je nodig hebt:
- Doekafmetingen (breedte × hoogte in cm)
- Oppervlakte per kleur (in m²)
- Montana Black dekking: 2-2.5 m² per bus
- Automatisch afronden naar boven voor voldoende verf

## Browser Compatibiliteit

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Vereist ondersteuning voor:
- HTML5 Canvas
- ES6 JavaScript
- FileReader API
- Blob API

## Licentie

MIT License - vrij te gebruiken voor persoonlijke en commerciële projecten.

---

- 👋 Hi, I'm @Jasperdeveer
- 👀 I'm interested in graphic design, photography and music production
- 🌱 I'm currently learning jquery and react
- 📫 Info@jasperdeveer.nl
