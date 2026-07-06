# AI Briefing: JSPR Beamer Setup - Paint-by-Numbers Desktop Applicatie

## 📋 Project Overview

Bouw een high-performance desktop applicatie voor het genereren van paint-by-numbers templates, geoptimaliseerd voor beamer projectie bij street art en muurschilderingen. De applicatie moet 10-100x sneller zijn dan browser-gebaseerde alternatieven door gebruik van native Python libraries.

**Primaire Use Case:** Kunstenaars projecteren een paint-by-numbers template op een muur, waarbij elk gebied een nummer heeft dat correspondeert met een kleur. De app moet in real-time projectie ondersteunen met keyboard-only controls.

**Target Platform:** macOS (Intel + Apple Silicon M1/M2/M3) en Linux desktop
**Primary Language:** Python 3.8+
**GUI Framework:** PyQt5

---

## 🎯 Scope & Core Requirements

### IN SCOPE ✅

#### 1. Image Processing & Analysis
- **K-means Color Clustering**
  - Gebruik scikit-learn voor snelle clustering (0.5-1s vs 5-10s in browser)
  - Gebruiker kan 2-32 kleuren kiezen
  - Automatische color quantization van originele afbeelding

- **Manual Color Selection (Eyedropper Tool)**
  - Pipet tool om handmatig kleuren te picken uit afbeelding
  - Click op afbeelding → sample kleur → toevoegen aan palette
  - Automatische duplicate detection
  - Toevoegen aan bestaande palette mogelijk

- **Edge Detection**
  - OpenCV-based multi-scale edge detection (0.02s vs 2-3s in browser)
  - Canny edge detection + Harris corner detection
  - Contour tracing met findContours (veel sneller dan Marching Squares)
  - Ramer-Douglas-Peucker simplification voor gladde lijnen

- **Region Analysis**
  - Distance transform voor centrum-detectie per regio
  - Minimum region size filter (10-500 pixels)
  - Intelligent number placement (centered in regions)

#### 2. Visualization Modes
De app moet drie visualisatie modes ondersteunen:

**Mode 1: Origineel**
- Toont onbewerkte input image

**Mode 2: Paint-by-Numbers**
- Quantized afbeelding met kleuren uit palette
- Zwarte contour lijnen (instelbare dikte 1-10px)
- Nummers in elk gebied (zwart, gecentreerd)
- Kleuren palette zichtbaar in sidebar

**Mode 3: Lijntekening**
- Alleen zwarte lijnen op witte achtergrond
- Nummers in elk gebied
- Minimalistische stijl voor projectie

#### 3. Presentation Mode (Beamer Projectie) 🎨
Dit is een **kritieke feature** - fullscreen keyboard-controlled modus voor projectie:

**Display Features:**
- Fullscreen viewer (zwarte achtergrond)
- Zoom: 10% - 500% (met smooth scaling)
- Pan: arrow keys of mouse drag
- Grid overlay met instelbare kleuren

**Grid System:**
- Overlay grid met labels (A1, A2, B1, B2, etc.)
- Cijfertoetsen 1-6 → instant switch naar 1x1, 2x2, 3x3, 4x4, 5x5, 6x6 grid
- `[` en `]` toetsen voor +/- grid grootte
- `Shift` + `+/-` ook voor grid grootte
- Grid kleuren: Gifgroen (neon), Magenta, Cyaan, Geel (wisselen met `C`)
- Dikke lijnen (3px) voor zichtbaarheid op beamer

**Keyboard Controls (VOLLEDIG KEYBOARD-ONLY):**
```
ESC / Q          → Afsluiten presentatie mode
F11              → Toggle fullscreen
H                → Toggle keyboard shortcuts overlay
N                → Toggle nummers aan/uit
O                → Toggle outlines aan/uit
G                → Toggle grid overlay aan/uit
C                → Cycle grid kleur (groen/magenta/cyaan/geel)
1-6              → Direct set grid naar 1x1 t/m 6x6
[ / ]            → Grid grootte +/-
Shift + +/-      → Grid grootte +/-
Space            → Cycle door modes (origineel/paint-by-numbers/lijntekening)
+ / -            → Zoom in/uit (25% stappen)
Z                → Handmatig zoom percentage invoeren (popup)
0                → Reset zoom en pan
←↑→↓             → Pan beeld (50px stappen)
Muiswiel         → Zoom in/uit (2% per scroll)
Shift + Muiswiel → Snelle zoom (10% per scroll)
Pinch (trackpad) → Natuurlijke zoom zoals Photoshop
Mouse drag       → Pan beeld
```

**UI Overlays:**
- Auto-fading keyboard shortcuts overlay (verdwijnt na 3 seconden, komt terug bij toets)
- Status bar rechtsonder: "Zoom: 150% | Nummers: ON | Grid: 4x4 (Gifgroen)"
- Zoom percentage clickable voor handmatige input
- Hover effect op interactive elements

**Dynamic Quality Rendering:**
- Bij zoom > 2x → regenerate image in hogere kwaliteit
- Quality thresholds: 0.5x, 0.75x, 1x, 1.5x, 2x, 3x, 4x
- Emits signal naar main window voor re-render wanneer threshold crossed

#### 4. Color Management
- Intelligent color naming gebaseerd op HSV values
  - Voorbeelden: "Rood", "Lichtblauw", "Donkergroen", "Paars", "Oranje"
- Automatic similar color merging (optioneel)
- Sorteer kleuren op hue/brightness
- Color palette editor:
  - Verwijder kleuren
  - Merge kleuren
  - Handmatig toevoegen (eyedropper)
- Undo/redo support

#### 5. Export Functionality
- **PNG Export** met configureerbare DPI
  - High-res voor printen (300 DPI)
  - Standard voor scherm (72 DPI)
- **SVG Export** voor vector graphics
  - Schaalbaar zonder kwaliteitsverlies
  - Bewaar contours als paths
- Keyboard shortcut: `Cmd+E` / `Ctrl+E`

#### 6. UI/UX Requirements

**Main Window Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Menu Bar (File, Edit, View, Help)                  │
├──────────┬──────────────────────────┬───────────────┤
│          │                          │               │
│  Left    │       Canvas             │   Right       │
│  Panel   │      (Main View)         │   Panel       │
│          │                          │               │
│ Controls │   Resizable Splitters    │   Legend      │
│          │                          │               │
│  280-420 │      (Expanding)         │   220-380     │
│   px     │                          │     px        │
│          │                          │               │
├──────────┴──────────────────────────┴───────────────┤
│ Shortcuts Widget (Auto-hiding, responsive)         │
└─────────────────────────────────────────────────────┘
```

**Left Panel - Controls:**
- Image load button (prominent)
- Color count slider/spinner (2-32)
- "Detecteer Kleuren" button (triggers K-means)
- "🎨 Pipet (Kleur Kiezen)" button voor eyedropper
- Visualization mode toggle (3 radio buttons)
- Line width slider (1-10px)
- Min region size slider (10-500px)
- "🖥️ Presentatie Mode" button (F11)
- Progress indicators tijdens processing

**Canvas (Center):**
- Scroll & zoom ondersteuning
- Mouse wheel zoom (Ctrl+wheel voor fijnmaziger)
- Fit-to-window by default
- Pan met mouse drag of arrow keys
- Eyedropper cursor wanneer actief

**Right Panel - Legend:**
- Scrollable color list
- Voor elke kleur:
  - Nummer
  - Color swatch (grote vierkant)
  - RGB/HEX waarde
  - Nederlandse kleurnaam
  - Delete button
- Sorteer opties: Hue, Brightness, Nummer

**Shortcuts Widget (Bottom):**
- 4 kolommen met shortcuts
- Minimum 110px breed per kolom
- Scrollable horizontaal bij kleine schermen
- Dark glassmorphism styling (#1e1e1e met transparency)
- Responsive: verbergt automatisch bij smalle vensters

**Resizable Splitters:**
- QSplitter met 8px brede handles
- Visible handles met hover effect (blauw highlight)
- Splitter handvatten tussen panelen
- Drag met muis om panel grootte aan te passen
- Standaard verdeling: 18% left, 64% center, 18% right

**Styling Theme:**
- Dark glassmorphism design
- Semi-transparent panels met blur effects
- Color scheme: #0f0f0f (achtergrond), #191919 (panels)
- Accent color: #667ee6 (blauw)
- Button styling:
  - 32px min height
  - Rounded corners (5px)
  - Hover effects (lighter background)
  - Checked state (blauw highlight)
- Font: Sans-serif, 11-14pt

#### 7. Performance Requirements

**Speed Benchmarks vs Browser (JavaScript):**
| Operation | Browser | Desktop | Target Speedup |
|-----------|---------|---------|----------------|
| K-means clustering | 5-10s | 0.5-1s | 10x faster |
| Edge detection | 2-3s | 0.02s | 100x faster |
| Image quantization | 1-2s | 0.05s | 20-40x faster |
| Contour tracing | 1-2s | 0.1s | 10-20x faster |

**Requirements:**
- K-means moet binnen 1 seconde voor 1920x1080 afbeelding
- Edge detection moet < 50ms
- UI moet responsive blijven (geen freezing tijdens processing)
- Use threading/multiprocessing voor heavy operations
- Progress dialogs voor operations > 500ms

#### 8. File Operations
- **Open**: PNG, JPG, JPEG, BMP (via Pillow + OpenCV)
- **Recent files**: Track laatste 10 geopende bestanden
- **Auto-save**: Optioneel auto-save van project state (JSON)
- Keyboard shortcuts:
  - `Cmd+O` / `Ctrl+O` → Open
  - `Cmd+E` / `Ctrl+E` → Export
  - `Cmd+Q` / `Ctrl+Q` → Quit

#### 9. Multi-Platform Launcher System

**Git Workflow:**
- Twee branches: `stable` (productie) en `dev` (development)
- Version selector popup bij launch (PyQt5 dialog)
- Twee grote buttons:
  - Groene button: "✓ Stable Versie" (aanbevolen)
  - Oranje button: "⚡ Development Versie" (experimenteel)

**Scripts (Bash):**
```
setup.sh              → Automatische installatie (Python check, venv, dependencies)
launch.sh             → Start app met version selector GUI
run_stable.sh         → Direct stable versie starten
run_dev.sh            → Direct dev versie starten
update_stable.sh      → Git pull stable branch (met 10s timeout)
update_dev.sh         → Git pull dev branch (met 10s timeout)
merge_dev_to_stable.sh → Merge dev naar stable (met confirmatie)
```

**Offline Support:**
- Alle git pull/fetch operaties met `timeout` command
- Timeouts: 3-10 seconden
- Graceful fallback: "(Offline - using local version)"
- App moet altijd starten, ook zonder internet
- Geen hanging bij netwerkproblemen

**macOS specifiek:**
- `.app` bundle support
- `Start JSPR Beamer.command` voor dubbelklik launch
- Terminal.app launcher voor macOS
- Dock icon support

**Linux specifiek:**
- `.desktop` file voor system integration
- Application menu integratie
- XDG Desktop Entry

#### 10. Installation & Setup

**Automated Installer (`setup.sh`):**
```bash
1. Detect OS (macOS/Linux)
2. Check Python versie (3.8+ required)
3. Create virtual environment
4. Install dependencies from requirements.txt
5. Verify installation (PyQt5, OpenCV, sklearn)
6. Configure OS-specific launchers
7. Show success message met usage instructions
```

**Dependencies (requirements.txt):**
```
PyQt5>=5.15.10
opencv-python>=4.8.0
opencv-contrib-python>=4.8.0
numpy>=1.24.0,<2.0.0
Pillow>=10.0.0
scikit-learn>=1.3.0
scikit-image>=0.22.0
svgwrite>=1.4.0
scipy>=1.11.0
py2app>=0.28.0  # macOS only
pytest>=7.4.0   # Development
```

**Documentation:**
- `INSTALL.md`: Volledige installatie instructies
- `README.md`: Feature overview + quick start
- `README_WORKFLOW.md`: Git workflow uitleg (stable/dev)

---

### OUT OF SCOPE ❌

**Expliciet NIET implementeren:**
- Web interface / browser versie
- Cloud sync / online storage
- User accounts / authentication
- Multi-user collaboration
- Mobile apps (iOS/Android)
- Windows ondersteuning (alleen macOS/Linux)
- Real-time collaboration
- Plugin systeem
- AI/ML model training (alleen inference)
- 3D projection mapping
- Video input (alleen static images)
- Printing functionaliteit (alleen export)
- Batch processing van meerdere afbeeldingen tegelijk

---

## 🏗️ Technical Architecture

### Core Modules

**1. `main_window.py` (3000-4000 lines)**
- PyQt5 main window met QSplitter layout
- Menu bar (File, Edit, View, Help)
- Three-panel layout (controls, canvas, legend)
- ShortcutsWidget integration
- Event handling voor alle UI interactions
- Signal/slot connections tussen componenten
- Presentation mode launcher

**2. `image_processor.py` (1500-2000 lines)**
- K-means clustering met sklearn
- OpenCV edge detection (Canny + Harris corners)
- Image quantization
- Contour detection met findContours
- Region analysis met distance transform
- Multi-threading voor heavy operations
- Progress callbacks

**3. `color_manager.py` (800-1000 lines)**
- Color palette management
- HSV-based color naming (Nederlands)
- Similar color merging algoritme
- Undo/redo stack
- Color sorting (hue, brightness, number)
- Eyedropper tool integration

**4. `contour_tracer.py` (600-800 lines)**
- OpenCV contour detection
- Ramer-Douglas-Peucker simplification
- Corner preservation
- Region center detection
- Contour hierarchy management

**5. `visualizer.py` (1000-1200 lines)**
- Rendering engine voor 3 modes
- Cached rendering (geen herberekening)
- Number placement optimization
- Contour drawing met configurable width
- Export naar PNG/SVG
- High-DPI support

**6. `presentation_mode.py` (600-700 lines)**
- QWidget fullscreen window
- Grid overlay system met labels
- Keyboard event handling (alle shortcuts)
- Zoom/pan met smooth scaling
- Mouse drag support
- Trackpad pinch gesture (QGesture)
- Auto-fading shortcuts overlay
- Dynamic quality rendering signals
- Status bar rendering

**7. `stylesheet.py` (200-300 lines)**
- Glassmorphism theme CSS
- Dark mode color scheme
- Button/input styling
- Splitter handle styling
- Responsive breakpoints

**8. `version_launcher.py` (200-250 lines)**
- PyQt5 dialog voor version selectie
- Groene/oranje buttons (stable/dev)
- Git branch switching
- Direct launch van main.py
- Error handling met fallback

### Data Flow

```
User Input (Image)
    ↓
Image Processor (K-means + Edge Detection)
    ↓
Color Manager (Palette + Naming)
    ↓
Contour Tracer (Region Detection)
    ↓
Visualizer (Render Mode 1/2/3)
    ↓
Main Canvas (Display)
    ↓
Presentation Mode (Fullscreen Beamer)
```

### Threading Model
- Main thread: UI (PyQt5 event loop)
- Worker thread: K-means clustering
- Worker thread: Edge detection
- Worker thread: Contour tracing
- All workers emit progress signals naar main thread

### File Structure
```
paint-by-numbers-desktop/
├── src/
│   ├── main_window.py         # Main UI window
│   ├── image_processor.py     # Image processing core
│   ├── color_manager.py       # Color palette management
│   ├── contour_tracer.py      # Contour detection
│   ├── visualizer.py          # Rendering engine
│   ├── presentation_mode.py   # Fullscreen beamer mode
│   └── stylesheet.py          # Glassmorphism styling
├── assets/
│   ├── icon.png               # App icon (512x512)
│   └── app_icon.icns          # macOS icon
├── main.py                    # Entry point met splash screen
├── version_launcher.py        # Version selector GUI
├── requirements.txt           # Python dependencies
├── setup.sh                   # Automated installer
├── launch.sh                  # Main launcher
├── run_stable.sh              # Stable launcher
├── run_dev.sh                 # Dev launcher
├── update_stable.sh           # Stable updater
├── update_dev.sh              # Dev updater
├── merge_dev_to_stable.sh     # Branch merger
├── Start JSPR Beamer.command  # macOS launcher
├── jspr-beamer.desktop        # Linux desktop entry
├── README.md                  # Main documentation
├── INSTALL.md                 # Installation guide
└── README_WORKFLOW.md         # Git workflow guide
```

---

## 🎨 UI Implementation Details

### ShortcutsWidget
```python
class ShortcutsWidget(QWidget):
    """Responsive keyboard shortcuts display"""
    - QScrollArea met horizontal scroll
    - 4 columns: Algemeen, Bestand, Weergave, Navigatie
    - Minimum 110px per column (prevents overlap)
    - Dark background (#1e1e1e, 95% opacity)
    - Font: 11-14pt, semi-bold voor titels
    - Auto-hide bij venster < 800px breed
    - Try-catch voor graceful fallback
```

### Canvas Widget
```python
class PaintByNumbersCanvas(QLabel):
    """Scrollable zoomable canvas"""
    - QLabel met QPixmap
    - Wheel event voor zoom
    - Mouse tracking voor pan & eyedropper
    - Fit-to-window by default
    - Cache rendered QPixmap
    - Eyedropper: setCursor(Qt.CrossCursor)
```

### Color Legend Widget
```python
class ColorLegendWidget(QWidget):
    """Scrollable color palette display"""
    - QScrollArea met vertical scroll
    - Per color:
      * QFrame container (10px padding)
      * QLabel met number (bold, 14pt)
      * Color swatch (50x50px QWidget)
      * QLabel met RGB (mono font, 9pt)
      * QLabel met name (11pt)
      * QPushButton delete (icon: 🗑️)
    - Sort buttons: By Hue, By Brightness, By Number
```

### Presentation Mode Window
```python
class PresentationMode(QWidget):
    """Fullscreen beamer projection window"""
    - Inherit from QWidget (not QMainWindow)
    - setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
    - showFullScreen() by default
    - Black background
    - Custom paintEvent voor:
      * Image rendering (scaled + panned)
      * Grid overlay (lines + labels)
      * Shortcuts overlay (auto-fading)
      * Status bar (bottom-right)
    - grabGesture(Qt.PinchGesture)
    - mousePressEvent/mouseMoveEvent voor drag
    - wheelEvent voor zoom
    - keyPressEvent voor alle shortcuts
```

### Version Selector Dialog
```python
class VersionSelectorDialog(QDialog):
    """Modern version choice popup"""
    - Fixed size: 500x280px
    - Modal dialog
    - Two large buttons (60px height):
      * Stable: #2ecc71 green
      * Dev: #e67e22 orange
    - Dark background (#2c3e50)
    - Hover effects (lighter colors)
    - Descriptive text under buttons
    - Fusion style for modern look
```

---

## 🧪 Testing Requirements

### Unit Tests (pytest)
- K-means clustering output verificatie
- Edge detection correctness
- Color naming algorithm
- Contour simplification accuracy
- Export format validation (PNG/SVG)

### Integration Tests
- Full pipeline: Image → Process → Render → Export
- UI interactions: Button clicks, keyboard shortcuts
- Version selector → branch switching → app launch
- Offline mode: Timeouts, fallbacks

### Manual Testing Checklist
```
□ Open verschillende image formaten (PNG, JPG, BMP)
□ K-means met 5, 15, 30 kleuren
□ Eyedropper tool: color picking & duplicate detection
□ Export naar PNG & SVG
□ Presentatie mode: alle keyboard shortcuts
□ Grid overlay: 1x1 t/m 6x6, alle kleuren
□ Zoom: 10% - 500%, mouse wheel, pinch gesture
□ Pan: arrow keys, mouse drag
□ Splitter handles: resizable panels
□ Version selector: stable & dev launch
□ Offline mode: start zonder internet binnen 5 seconden
□ Recent files laden
□ Auto-save functionaliteit
□ Window resize & responsive layout
□ macOS: .app bundle launch, dock icon
□ Linux: .desktop entry, application menu
```

### Performance Testing
- Benchmark K-means: moet < 1s voor 1920x1080
- Edge detection: moet < 50ms
- UI responsiveness: geen freezing
- Memory usage: max 500MB voor 4K afbeelding
- Startup tijd: < 3 seconden

---

## 📦 Delivery Criteria

### Minimaal Viable Product (MVP)
✅ Alles in "IN SCOPE" moet geïmplementeerd zijn
✅ Alle keyboard shortcuts werken
✅ Presentation mode volledig functioneel
✅ Offline mode werkt zonder hangen
✅ Version selector werkend
✅ Export naar PNG & SVG
✅ Eyedropper tool werkend
✅ Splitter handles dragbaar
✅ Trackpad pinch-to-zoom

### Code Quality
- Type hints waar mogelijk (Python 3.8+ compatible)
- Docstrings voor alle classes & public methods
- Error handling met try-catch
- Logging met Python logging module
- Comments voor complexe algoritmes
- No hardcoded paths (gebruik os.path)

### Documentation
- README.md met features, usage, screenshots
- INSTALL.md met stap-voor-stap installatie
- README_WORKFLOW.md met git branching uitleg
- Inline code comments voor complexe delen
- Docstrings in Engels, UI tekst in Nederlands

### Platform Support
- macOS Intel: Volledig getest
- macOS Apple Silicon (M1/M2/M3): Volledig getest
- Linux (Ubuntu 20.04+): Volledig getest
- Alle launchers werken on/offline

---

## 💡 Implementation Tips

### 1. Start met Main Window Skeleton
Begin met een basic PyQt5 window met 3 panels en menu bar. Test dat splitters werken voordat je verder gaat.

### 2. Implementeer Image Processor First
K-means + edge detection zijn de kern. Test deze grondig met verschillende afbeeldingen voordat je verder gaat.

### 3. Presentation Mode is Kritiek
Dit is de meest complexe feature. Alloceer 30-40% van de tijd hier. Test alle keyboard shortcuts uitvoerig.

### 4. Gebruik Threading Correct
PyQt5 threading met QThread + signals/slots. Never block main thread.

### 5. Cache Agressief
- Rendered images cachen (QPixmap)
- K-means resultaten cachen
- Contours cachen
- Alleen re-render bij wijzigingen

### 6. Error Handling Overal
- Try-catch bij file operations
- Fallbacks bij network timeouts
- Graceful degradation bij missing resources
- User-friendly error messages (Nederlands)

### 7. Test Offline Mode Vroeg
Zorg dat alle git operations timeouts hebben. Test met airplane mode.

### 8. Git Workflow Setup
Maak direct `stable` en `dev` branches. Test version selector grondig.

---

## 🚀 Success Metrics

**Functionaliteit:**
- ✅ Alle features uit IN SCOPE werken
- ✅ Geen crashes bij normale usage
- ✅ Offline mode werkt zonder hangen

**Performance:**
- ✅ 10x+ sneller dan browser versie
- ✅ K-means < 1s voor 1920x1080
- ✅ UI blijft responsive

**User Experience:**
- ✅ Intuïtieve UI, geen tutorial nodig
- ✅ Presentation mode werkt volledig keyboard-only
- ✅ Grid overlay direct bruikbaar voor projectie

**Deployment:**
- ✅ `setup.sh` installeert alles automatisch
- ✅ Launchers werken on/offline
- ✅ Documentatie compleet

---

## 📞 Contact & Questions

Bij onduidelijkheden:
1. Check README.md voor feature details
2. Check code comments voor implementation details
3. Test bestaande functionaliteit om gedrag te begrijpen
4. Vraag specifieke verduidelijking als nodig

**Belangrijkste referenties:**
- OpenCV documentation voor image processing
- PyQt5 documentation voor UI
- scikit-learn voor K-means
- Git branching best practices

---

**Geschatte Implementatie Tijd:** 40-60 uur voor ervaren Python/PyQt5 developer

**Prioriteit Volgorde:**
1. Image processor (K-means + edge detection) - 30%
2. Presentation mode (fullscreen + shortcuts) - 30%
3. Main window UI (panels + controls) - 20%
4. Launcher system (version selector + offline) - 10%
5. Export & polish - 10%

Veel succes met de implementatie! 🎨🚀
