#!/bin/bash

# JSPR Beamer Setup - Automatische Installatie
# Werkt op macOS en Linux

set -e  # Stop bij errors

echo ""
echo "🎨 JSPR Beamer Setup - Automatische Installatie"
echo "================================================"
echo ""

# Detecteer OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    echo "🍎 Besturingssysteem: macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
    echo "🐧 Besturingssysteem: Linux"
else
    echo "❌ Niet-ondersteund besturingssysteem: $OSTYPE"
    exit 1
fi

echo ""

# Check Python
echo "📋 Stap 1/5: Python versie controleren..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 niet gevonden!"
    echo ""
    if [[ "$OS" == "macOS" ]]; then
        echo "Installeer Python via: https://www.python.org/downloads/"
        echo "Of via Homebrew: brew install python@3.11"
    else
        echo "Installeer Python via: sudo apt install python3 python3-pip python3-venv"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
echo "✓ Python $PYTHON_VERSION gevonden"

# Check minimale Python versie (3.8+)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "❌ Python versie te oud! Minimaal vereist: 3.8"
    echo "   Jouw versie: $PYTHON_VERSION"
    exit 1
fi

echo ""

# Check Git
echo "📋 Stap 2/5: Git controleren..."
if ! command -v git &> /dev/null; then
    echo "⚠️  Git niet gevonden (optioneel voor updates)"
else
    GIT_VERSION=$(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    echo "✓ Git $GIT_VERSION gevonden"
fi

echo ""

# Virtual Environment
echo "📋 Stap 3/5: Virtual environment aanmaken..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment bestaat al"
    read -p "   Opnieuw aanmaken? (j/n): " RECREATE
    if [[ "$RECREATE" =~ ^[jJ]$ ]]; then
        echo "   Verwijderen oude venv..."
        rm -rf venv
    else
        echo "   Bestaande venv wordt gebruikt"
    fi
fi

if [ ! -d "venv" ]; then
    echo "   Aanmaken virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment aangemaakt"
else
    echo "✓ Virtual environment klaar"
fi

echo ""

# Activeer venv
echo "📋 Stap 4/5: Dependencies installeren..."
echo "   (Dit kan 5-10 minuten duren...)"
echo ""

source venv/bin/activate

# Upgrade pip
echo "   Upgraden pip..."
pip install --upgrade pip --quiet

# Installeer dependencies
echo "   Installeren packages (wees geduldig)..."
echo ""

# Installeer met progress
pip install -r requirements.txt

echo ""
echo "✓ Alle dependencies geïnstalleerd"

# Verifieer installatie
echo ""
echo "📋 Stap 5/5: Installatie verifiëren..."

# Test PyQt5
if python3 -c "from PyQt5.QtWidgets import QApplication; import sys; app = QApplication(sys.argv)" 2>/dev/null; then
    echo "✓ PyQt5 werkt"
else
    echo "❌ PyQt5 test gefaald"
    exit 1
fi

# Test OpenCV
if python3 -c "import cv2" 2>/dev/null; then
    echo "✓ OpenCV werkt"
else
    echo "❌ OpenCV test gefaald"
    exit 1
fi

# Test scikit-learn
if python3 -c "from sklearn.cluster import KMeans" 2>/dev/null; then
    echo "✓ scikit-learn werkt"
else
    echo "❌ scikit-learn test gefaald"
    exit 1
fi

deactivate

echo ""

# Maak scripts uitvoerbaar
echo "🔧 Scripts uitvoerbaar maken..."
chmod +x *.sh 2>/dev/null || true
chmod +x "Start JSPR Beamer.command" 2>/dev/null || true

# OS-specifieke setup
if [[ "$OS" == "Linux" ]]; then
    echo ""
    echo "🐧 Linux-specifieke setup..."

    # Desktop entry installeren
    if [ -f "jspr-beamer.desktop" ]; then
        DESKTOP_DIR="$HOME/.local/share/applications"
        mkdir -p "$DESKTOP_DIR"

        # Update paths in desktop file
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        sed -i "s|Exec=.*|Exec=$SCRIPT_DIR/launch.sh|g" jspr-beamer.desktop
        sed -i "s|Icon=.*|Icon=$SCRIPT_DIR/assets/icon.png|g" jspr-beamer.desktop

        cp jspr-beamer.desktop "$DESKTOP_DIR/"
        chmod +x "$DESKTOP_DIR/jspr-beamer.desktop"

        # Update desktop database
        if command -v update-desktop-database &> /dev/null; then
            update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
        fi

        echo "✓ Desktop entry geïnstalleerd"
        echo "  Je kunt de app vinden in je applicatie menu"
    fi
elif [[ "$OS" == "macOS" ]]; then
    echo ""
    echo "🍎 macOS-specifieke setup..."

    if [ -d "JSPR Beamer Setup.app" ]; then
        echo "✓ App bundle gevonden"
        echo "  Sleep 'JSPR Beamer Setup.app' naar je Dock voor snelle toegang"
    fi

    if [ -f "Start JSPR Beamer.command" ]; then
        echo "✓ Launcher command gevonden"
        echo "  Dubbelklik 'Start JSPR Beamer.command' om te starten"
    fi
fi

echo ""
echo "================================================"
echo "✅ Installatie succesvol voltooid!"
echo "================================================"
echo ""
echo "Je kunt de app nu starten op verschillende manieren:"
echo ""

if [[ "$OS" == "macOS" ]]; then
    echo "  1️⃣  Dubbelklik 'Start JSPR Beamer.command' in Finder"
    echo "  2️⃣  Of via terminal: ./launch.sh"
    echo "  3️⃣  Stable versie: ./run_stable.sh"
    echo "  4️⃣  Dev versie: ./run_dev.sh"
else
    echo "  1️⃣  Zoek 'JSPR Beamer Setup' in je applicatie menu"
    echo "  2️⃣  Of via terminal: ./launch.sh"
    echo "  3️⃣  Stable versie: ./run_stable.sh"
    echo "  4️⃣  Dev versie: ./run_dev.sh"
fi

echo ""
echo "📖 Meer info:"
echo "  - Installatie handleiding: cat INSTALL.md"
echo "  - Git workflow: cat README_WORKFLOW.md"
echo ""
echo "Bij de eerste start krijg je een popup om te kiezen tussen:"
echo "  • Stable versie (groen) - Aanbevolen, geteste versie"
echo "  • Development versie (oranje) - Nieuwste features"
echo ""
echo "Veel plezier! 🎨"
echo ""
