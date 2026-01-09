# 🎨 Paint-by-Numbers Generator - Street Art Editie (v6.0 AI Pro)

Een professionele web applicatie voor het converteren van afbeeldingen naar paint-by-numbers sjablonen, speciaal ontworpen voor street art en spuitbus projecten.

**🤖 Nieuw in v6.0: AI-Powered Edge Detection + Corner Preservation** - Multi-scale edge detection met Harris corner detector voor perfecte hoekbehoud en detail preservatie!

**📊 Nieuw in v6.0: Real-time Progress Bar** - Zie exact waar de AI mee bezig is tijdens het verwerken van je afbeelding!

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
3. **Lijntekening** - 🤖 **AI-Powered Edge Detection Pro** met maximale precisie
   - **Multi-Scale Edge Detection** 🆕 - detecteert details op 3 schalen (fijn/medium/grof)
   - **Harris Corner Detector** 🆕 - behoudt scherpe hoeken automatisch
   - **Angle Threshold Detection** 🆕 - hoeken scherper dan 120° worden niet gesmoothd
   - **Real-time Progress Bar** 🆕 - zie wat de AI doet tijdens processing
   - **Bilateral Filtering** - edge-preserving noise reduction
   - **Adaptive Thresholding** - intelligente drempelwaarde bepaling
   - **Non-Maximum Suppression** - pixel-perfecte lijn dikte
   - **Hysteresis Edge Tracking** - verbindt zwakke edges met sterke
   - **Morphological Operations** - elimineert gaten en ruis
   - **Zhang-Suen Thinning** - ultradunne, precieze lijnen
   - **Corner-Aware Smoothing** 🆕 - Chaikin smoothing die hoeken behoudt
   - **Marching Squares** voor vloeiende contouren
   - **Ramer-Douglas-Peucker** lijn simplificatie
   - Cijfers met **witte outline** voor maximale zichtbaarheid
   - **Meer nummers** door lagere minimale vlakgrootte (20px)

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

- **TensorFlow.js** (optioneel) - AI/ML framework voor advanced image processing
- **Vanilla JavaScript** (ES6+)
- **HTML5 Canvas API** voor beeldverwerking
- **K-means clustering** voor kleurdetectie
- **AI-Powered Edge Detection**:
  - Bilateral Filtering
  - Adaptive Thresholding
  - Non-Maximum Suppression
  - Hysteresis Edge Tracking
  - Morphological Operations (Dilation/Erosion)
  - Zhang-Suen Thinning Algorithm
- **Advanced contour tracing** met Marching Squares
- **Ramer-Douglas-Peucker** algoritme voor lijn simplificatie
- **Chaikin's corner cutting** voor curve smoothing
- **Catmull-Rom splines** (optioneel) voor perfecte curves
- **Flood fill algoritme** voor regio detectie
- **SVG generation** voor vector export

## Algoritmes

### Kleurdetectie
Gebruikt K-means clustering om de meest dominante kleuren in een afbeelding te identificeren. Het algoritme:
1. Neemt willekeurige pixels als sample (voor performance)
2. Initialiseert centroids
3. Itereert tot convergentie
4. Genereert automatisch kleurnamen

### Enhanced Line Drawing
**Nieuwe precisie-verbeterde lijntekening pipeline:**

1. **Contour Extraction**: Detecteert kleurengrenzen met pixel-perfecte nauwkeurigheid
2. **Marching Squares**: Converteert pixel boundaries naar vloeiende contouren
3. **Path Simplification**: Ramer-Douglas-Peucker algoritme reduceert onnodige punten
4. **Curve Smoothing**: Chaikin's corner cutting voor natuurlijke, gladde lijnen
5. **Optimized Rendering**: Canvas anti-aliasing en line cap/join optimalisaties

**Resultaat**: Strakke, professionele lijnen zonder pixelatie of trappende effecten.

### AI-Powered Edge Detection (v5.0) 🤖
**De meest geavanceerde edge detection pipeline:**

1. **Grayscale Conversion** - Luminance-based conversie voor optimale edge detectie
2. **Bilateral Filtering** - Edge-preserving noise reduction die ruis verwijdert maar edges behoudt
3. **Sobel Gradient Calculation** - Berekent gradient magnitude en richting met 3x3 kernels
4. **Non-Maximum Suppression** - Verdunt edges tot single-pixel breedte langs gradient richting
5. **Adaptive Thresholding** - Intelligente drempelwaarde bepaling op basis van lokale statistieken
6. **Hysteresis Edge Tracking** - Verbindt zwakke edges met sterke edges (iteratief)
7. **Morphological Closing** - Vult kleine gaten met dilation gevolgd door erosion
8. **Zhang-Suen Thinning** - Optionele ultra-thinning voor perfecte lijnen

**Voordelen t.o.v. klassieke Canny:**
- ✅ Edge-preserving smoothing (geen blur van belangrijke randen)
- ✅ Adaptieve thresholds (geen handmatige tuning nodig)
- ✅ Betere noise rejection door morphological operations
- ✅ Dunnere, preciezere lijnen door advanced thinning

### Number Visibility Enhancement
Cijfers worden getekend met een **witte outline** (stroke) om perfecte leesbaarheid te garanderen in alle visualisatie modes, vooral in de lijntekening mode. Minimale vlakgrootte verlaagd naar 20px voor meer nummers.

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
