# JSPR Beamer Setup - Desktop App

High-performance Python desktop application for paint-by-numbers generation with beamer projection support.

## Features

### Core Functionality
- **10-100x faster** than browser version using OpenCV + NumPy
- Native macOS application with PyQt5
- Advanced AI-powered edge detection
- Intelligent color detection and merging
- **Eyedropper tool** for manual color selection
- Real-time preview and editing
- Export to PNG/SVG

### Presentation Mode (Beamer Projection)
- Fullscreen presentation mode with keyboard controls
- Grid overlay system (A1, A2, B1, etc.)
- Auto-fading keyboard shortcuts overlay
- Real-time toggle numbers and modes
- Zoom & pan functionality
- Perfect for street art and mural projection

### Styling
- Glassmorphism/liquid glass design
- Dark theme optimized for beamer use
- Semi-transparent panels with blur effects

## Performance Comparison

| Operation | Browser (JavaScript) | Desktop (Python) | Speedup |
|-----------|---------------------|------------------|---------|
| K-means clustering | 5-10s | 0.5-1s | **10x** |
| Edge detection | 2-3s | 0.02s | **100x** |
| Image quantization | 1-2s | 0.05s | **20-40x** |
| Contour tracing | 1-2s | 0.1s | **10-20x** |

## Installation

### Requirements

- Python 3.9 or later
- macOS 10.14 or later (Intel or Apple Silicon)

### Install Dependencies

```bash
cd paint-by-numbers-desktop

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

### Quick Start (Development Mode)

```bash
# Easy one-command launcher
./run.sh
```

The `run.sh` script will:
- Create virtual environment if needed
- Install dependencies automatically
- Launch the application

### Build macOS App Bundle (.app)

For a standalone app you can double-click:

```bash
# Automated build script
./build.sh
```

The `build.sh` script will:
- Set up virtual environment
- Install all dependencies including py2app
- Clean previous builds
- Build the .app bundle
- Open dist folder in Finder

**Result:** `dist/JSPR Beamer Setup.app` - ready to use!

You can then:
- Double-click to launch (no terminal needed!)
- Move to /Applications folder
- Create a DMG for distribution

See [BUILD.md](BUILD.md) for detailed build instructions and troubleshooting.

## Usage

1. **Open Image**
   - File > Open... (Cmd+O)
   - Supports PNG, JPG, JPEG, BMP

2. **Detect Colors**

   **Automatic:**
   - Choose number of colors (2-32)
   - Click "Detecteer Kleuren"
   - Wait for K-means clustering to complete

   **Manual (Eyedropper):**
   - Click "🎨 Pipet (Kleur Kiezen)"
   - Click on the image to sample a color
   - Confirm to add to palette
   - Duplicate colors are automatically detected

3. **Choose Visualization Mode**
   - **Origineel**: Original image
   - **Paint-by-Numbers**: Quantized with contours + numbers
   - **Lijntekening**: Black lines on white background

4. **Adjust Parameters**
   - **Line width** (1-10): Thickness of contour lines
   - **Min region size** (10-500): Minimum pixels for number placement

5. **Presentation Mode (Beamer Projection)**
   - Press F11 or click 🖥️ Presentatie Mode
   - Fullscreen view optimized for projection
   - **Keyboard shortcuts:**
     - `ESC` or `Q`: Exit presentation mode
     - `F11`: Toggle fullscreen
     - `N`: Toggle numbers
     - `G`: Toggle grid overlay
     - `H`: Toggle shortcuts help
     - `+`/`-`: Zoom in/out
     - `0`: Reset zoom
     - `Arrow keys`: Pan the view
     - `Space`: Cycle through modes

6. **Export**
   - File > Export PNG (Cmd+E)
   - Save your paint-by-numbers template

## Architecture

### Core Components

- **`image_processor.py`**: OpenCV-based image processing
  - K-means clustering with sklearn
  - Multi-scale edge detection
  - Harris corner detection
  - Image quantization

- **`color_manager.py`**: Color palette management
  - Intelligent color naming (HSV-based)
  - Automatic similar color merging
  - Undo/redo support
  - Color sorting

- **`contour_tracer.py`**: Contour detection and tracing
  - OpenCV findContours (much faster than Marching Squares)
  - Ramer-Douglas-Peucker simplification
  - Corner preservation
  - Region center detection with distance transform

- **`visualizer.py`**: Rendering engine
  - Multiple visualization modes
  - Cached rendering (no recomputation)
  - Number placement optimization
  - Contour drawing

- **`main_window.py`**: PyQt5 GUI
  - Native macOS interface
  - Control panel, canvas, legend
  - Eyedropper tool integration
  - Progress dialogs
  - Export functionality

- **`presentation_mode.py`**: Fullscreen presentation
  - Beamer projection optimized
  - Grid overlay with labels
  - Keyboard-only controls
  - Auto-fading shortcuts help
  - Zoom & pan functionality

- **`stylesheet.py`**: Glassmorphism theme
  - Liquid glass styling
  - Dark theme for projection
  - Semi-transparent panels

## Keyboard Shortcuts

- **Ctrl+O**: Open image
- **Ctrl+E**: Export PNG
- **Ctrl+Q**: Quit application
- **F11**: Presentation mode
- **+/-**: Zoom in/out in canvas
- **0**: Reset zoom

## Troubleshooting

### OpenCV Installation Issues

If OpenCV fails to install:
```bash
# Try installing via conda
conda install -c conda-forge opencv

# Or build from source
pip install --no-binary opencv-python opencv-python
```

### PyQt5 on Apple Silicon

If PyQt5 doesn't work on M1/M2/M3:
```bash
# Install using conda
conda install pyqt

# Or use PyQt6 (update imports in code)
pip install PyQt6
```

### Performance Issues

- Reduce image size if >4000px
- Lower color count for faster processing
- Disable AI edge detection for speed

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
flake8 src/
```

## License

© 2026 JSPR - For street art and spray paint projects

## Credits

- OpenCV for computer vision
- scikit-learn for K-means clustering
- PyQt5 for native GUI
- NumPy for fast array operations
