#!/bin/bash

# JSPR Beamer Setup Installer
# Installs the application to the system

set -e

echo "🎨 JSPR Beamer Setup Installer"
echo "==============================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  This installer is designed for Linux systems."
    echo "For other systems, you can run the app directly with ./run.sh"
    exit 1
fi

# Setup virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "📦 Setting up virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    source "$SCRIPT_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$SCRIPT_DIR/requirements.txt"
    echo "✓ Dependencies installed"
    echo ""
fi

# Update desktop file with correct paths
DESKTOP_FILE="$SCRIPT_DIR/jspr-beamer.desktop"
DESKTOP_INSTALL_DIR="$HOME/.local/share/applications"

echo "📝 Updating desktop file paths..."
sed -i "s|Exec=.*|Exec=$SCRIPT_DIR/launch.sh|g" "$DESKTOP_FILE"
sed -i "s|Icon=.*|Icon=$SCRIPT_DIR/assets/icon.png|g" "$DESKTOP_FILE"

# Create applications directory if it doesn't exist
mkdir -p "$DESKTOP_INSTALL_DIR"

# Copy desktop file
echo "📋 Installing desktop entry..."
cp "$DESKTOP_FILE" "$DESKTOP_INSTALL_DIR/"
chmod +x "$DESKTOP_INSTALL_DIR/jspr-beamer.desktop"

# Make launch script executable
chmod +x "$SCRIPT_DIR/launch.sh"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_INSTALL_DIR"
fi

echo ""
echo "✓ Installation complete!"
echo ""
echo "You can now:"
echo "  1. Launch from your application menu (search for 'JSPR Beamer Setup')"
echo "  2. Run directly: $SCRIPT_DIR/launch.sh"
echo "  3. Run in development mode: $SCRIPT_DIR/run.sh"
echo ""
echo "Enjoy! 🎨"
