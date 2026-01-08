# Paint-by-Numbers Generator - Professional Edition 🎨

**Optimale versie met OpenCV, Watershed Segmentation en SVG Export**

Deze Python versie is veel krachtiger dan de JavaScript webapp en gebruikt professionele image processing technieken voor perfecte, noise-vrije resultaten.

## 🚀 Waarom Deze Versie Beter Is

### JavaScript Webapp Beperkingen:
- ❌ Simpele edge detection (veel noise)
- ❌ Basis flood fill (traag, imperfect)
- ❌ Canvas rendering (niet schaalbaar)
- ❌ Beperkte morphological operations

### Python Versie Voordelen:
- ✅ **Watershed Algorithm** - perfecte region segmentation
- ✅ **OpenCV** - industriële image processing
- ✅ **Morphological Operations** - professionele noise removal
- ✅ **SVG Export** - infinitely scalable vector output
- ✅ **scikit-image** - wetenschappelijke image analysis
- ✅ **Sneller** - geoptimaliseerde C++ backend
- ✅ **Betere resultaten** - geen noise, perfecte lijnen

## 📦 Installatie

### Vereisten
- Python 3.8 of hoger
- pip (Python package manager)

### Stap 1: Install Dependencies

```bash
# Installeer alle benodigde packages
pip install -r requirements.txt
```

Dit installeert:
- `opencv-python` - Image processing
- `numpy` - Array operations
- `scikit-image` - Watershed segmentation
- `scikit-learn` - K-means clustering
- `Pillow` - Image loading
- `svgwrite` - SVG export
- `matplotlib` - Color analysis
- `scipy` - Scientific computing
- `PyQt5` - GUI framework

### Stap 2: Test de Installatie

```bash
python paint_by_numbers.py --help
```

Als dit werkt, ben je klaar!

## 🎯 Gebruik

### Optie 1: GUI Applicatie (Aanbevolen)

```bash
python paint_by_numbers_gui.py
```

**Features:**
- 🖼️ Visuele interface (zoals de webapp maar krachtiger)
- 🎨 Live preview van original, colored en line drawing modes
- ⚙️ Real-time parameter aanpassing
- 📊 Color legend met spray paint calculations
- 💾 Direct export naar SVG/PNG
- 🌙 Modern dark theme

**Workflow:**
1. Klik "Load Image" en selecteer je afbeelding
2. Pas parameters aan:
   - **Colors**: Aantal kleuren (2-32)
   - **Min Region**: Minimale region grootte in pixels (10-1000)
3. Klik "Generate Paint-by-Numbers"
4. Bekijk resultaat in verschillende modes
5. Export naar SVG (schaalbaar) of PNG

### Optie 2: Command Line

```bash
# Basis gebruik
python paint_by_numbers.py input.jpg

# Met custom parameters
python paint_by_numbers.py input.jpg -c 15 -m 300

# Alleen SVG export
python paint_by_numbers.py input.jpg --no-png

# Alleen PNG export
python paint_by_numbers.py input.jpg --no-svg
```

**Parameters:**
- `-c, --colors N` - Aantal kleuren (default: 12)
- `-m, --min-size N` - Minimum region size in pixels (default: 200)
- `--no-svg` - Skip SVG export
- `--no-png` - Skip PNG export

**Output:**
- `input_paintbynumbers.svg` - Schaalbare vector versie met lijnen en nummers
- `input_line.png` - Line drawing (zwarte lijnen op wit)
- `input_colored.png` - Paint-by-numbers view met kleuren
- Terminal output met color legend en spray paint calculations

## 🎨 Hoe Het Werkt

### 1. **K-means Color Detection**
```python
# Detecteert dominante kleuren met scikit-learn
kmeans = KMeans(n_clusters=n_colors, n_init=10, max_iter=300)
```
- Veel nauwkeuriger dan JavaScript implementatie
- Sorteert op frequency (meest voorkomende kleuren eerst)

### 2. **Image Quantization**
```python
# Reduceert afbeelding tot palette kleuren
# Vindt nearest color voor elke pixel
```
- Sneller door NumPy vectorization
- Nauwkeuriger color matching

### 3. **Watershed Segmentation** ⭐ (Key Innovation!)
```python
# Behandelt afbeelding als topografisch oppervlak
# Vindt watershed boundaries = perfecte regio grenzen
markers = cv2.watershed(image, markers)
```

**Dit is het grote verschil met de webapp!**
- Watershed is een geavanceerd segmentation algoritme
- Geen edge detection noise
- Perfecte region boundaries
- Industrie-standaard voor image segmentation

### 4. **Morphological Operations**
```python
# Remove noise met morphological opening
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
```
- Professional noise removal
- Veel effectiever dan simpele region merging

### 5. **Region Merging**
```python
# Merge kleine regions met grootste buur
# Iteratief proces tot alle noise weg is
```
- Gebruikt scikit-image region properties
- Intelligente neighbor detection

### 6. **SVG Export** 🎯
```python
# Export als infinite scalable vector graphics
# Perfect voor grootschalige street art
```
- Print op elke grootte zonder kwaliteitsverlies
- Professionele output voor print shops

## 🎯 Voorbeelden

### Voorbeeld 1: Basic Street Art
```bash
python paint_by_numbers.py graffiti.jpg -c 8 -m 500
```
- 8 kleuren (simpel, bold)
- Grote regions (500px minimum)
- Perfect voor grote muren

### Voorbeeld 2: Detailed Portrait
```bash
python paint_by_numbers.py portrait.jpg -c 20 -m 100
```
- 20 kleuren (meer detail)
- Kleinere regions toegestaan
- Voor gedetailleerde projecten

### Voorbeeld 3: GUI Workflow
```bash
python paint_by_numbers_gui.py
```
1. Load afbeelding
2. Start met defaults (12 colors, 200px min)
3. Bekijk result
4. Tweak parameters if needed
5. Re-generate
6. Export SVG voor printer

## 📊 Output Formats

### SVG (Aanbevolen voor Print)
- ✅ Infinitely scalable
- ✅ Perfect voor grote formaten
- ✅ Kleine file size
- ✅ Edit in Inkscape/Illustrator
- ✅ Professionele kwaliteit

**Gebruik voor:**
- Print shops
- Plotter cutting
- Grote muren
- Professionele projecten

### PNG (Voor Preview/Digital)
- ✅ Universal format
- ✅ Easy sharing
- ✅ Direct preview
- ❌ Fixed resolution

**Gebruik voor:**
- Social media
- Digital preview
- Documentation

## 🎨 Spray Paint Calculations

De tool berekent automatisch hoeveel spuitbussen je nodig hebt:

**Montana Black Coverage:**
- ~2-2.5 m² per can (average: 2.25 m²)

**Berekening:**
```
Region Area (pixels) → Area (m²) → Cans Needed
```

**Note:** Pixel-to-meter conversie is een ruwe schatting.
Voor exacte berekeningen:
1. Meet je muur (b.v. 5m × 3m = 15m²)
2. Print op schaal
3. Bereken ratio: wall_area / image_area
4. Multiply cans × ratio

## 🔧 Troubleshooting

### "Module not found" Error
```bash
pip install -r requirements.txt
```

### "Could not load image" Error
- Check of bestand bestaat
- Ondersteunde formaten: PNG, JPG, JPEG, BMP, TIFF
- Probeer afbeelding te converteren

### Te veel kleine regions
- Verhoog `min_region_size` parameter
- Start met 500, verlaag geleidelijk

### Te weinig detail
- Verhoog aantal kleuren (`-c` parameter)
- Verlaag `min_region_size`

### GUI werkt niet
- Check PyQt5 installatie: `pip install PyQt5`
- Probeer command-line versie

## 🚀 Performance Tips

### Grote Afbeeldingen (> 4000px)
```python
# Resize image eerst voor snellere processing
from PIL import Image
img = Image.open('huge.jpg')
img.thumbnail((2000, 2000))
img.save('resized.jpg')
```

### Snellere Processing
- Gebruik minder kleuren (6-10)
- Grotere min_region_size (300-500)
- Moderne CPU helpt veel

### Beste Kwaliteit
- Gebruik hoge resolutie input
- Export SVG (schaalbaar!)
- Meer kleuren voor detail (15-20)

## 📝 Vergelijking Met Webapp

| Feature | JavaScript Webapp | Python App |
|---------|------------------|------------|
| Edge Detection | Basic Canny | Watershed Segmentation |
| Noise Removal | Region merging | Morphological ops + merging |
| Speed | Slow (browser) | Fast (native) |
| Output | Canvas PNG | SVG + PNG |
| Scalability | Fixed resolution | Infinite (SVG) |
| Quality | Good | Excellent |
| Algorithms | Basic | Professional |

## 🎯 Aanbevolen Workflow

1. **Test eerst in GUI** om parameters te vinden
2. **Export SVG** voor final output
3. **Open SVG in Inkscape** voor editing indien nodig
4. **Print op schaal** of gebruik plotter
5. **Use spray calculations** voor materiaal planning

## 🤝 Volgende Stappen

Als je nog meer wilt:
- **Batch processing** voor meerdere afbeeldingen
- **Auto-optimization** van parameters
- **Custom color palettes** (Montana Black colors)
- **Direct printer integration**
- **Wall projection mode** (beamer guides)

Laat het weten als je specifieke features wilt!

## 📄 License

Voor persoonlijk gebruik en street art projecten.

---

**Made with ❤️ for street artists**

*Watershed > Edge Detection* 🌊
