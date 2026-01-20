#!/bin/bash

# JSPR Beamer Setup - Terminal Launcher Creator
# Maakt een .app die Terminal opent (geen permission issues!)

cd "$(dirname "$0")"

APP_NAME="JSPR Beamer Setup"

echo "🚀 JSPR Beamer Setup - Terminal App Maker"
echo "=========================================="
echo ""
echo "Dit maakt een .app die Terminal opent met je app."
echo "Voordeel: Geen macOS permission issues!"
echo ""

# Verwijder oude app
if [ -d "$APP_NAME.app" ]; then
    echo "🗑️  Removing old app..."
    rm -rf "$APP_NAME.app"
fi

# Maak AppleScript app
echo "📱 Creating AppleScript app..."

osacompile -o "$APP_NAME.app" << 'APPLESCRIPT'
on run
    tell application "Terminal"
        activate
        do script "cd ~/Documents/GitHub/Jasperdeveer/paint-by-numbers-desktop && echo '🚀 JSPR Beamer Setup' && echo '===================' && echo '' && echo '📥 Updating to latest version...' && git pull origin claude/enhance-line-drawing-precision-kyhzU 2>/dev/null && echo '' && echo '✅ Starting app...' && echo '' && source venv/bin/activate && python main.py; echo ''; echo '✅ App closed'; sleep 2; exit"
    end tell
end run
APPLESCRIPT

if [ $? -ne 0 ]; then
    echo "❌ Failed to create app!"
    echo ""
    echo "Note: osacompile might not work in all environments"
    exit 1
fi

# Probeer icoon toe te voegen
if [ -f "app_icon.icns" ]; then
    echo "🎨 Adding icon..."
    ICON_DIR="$APP_NAME.app/Contents/Resources"
    if [ -d "$ICON_DIR" ]; then
        cp app_icon.icns "$ICON_DIR/applet.icns" 2>/dev/null && echo "   ✓ Icon added"
    fi
elif [ -f "assets/app_icon.icns" ]; then
    echo "🎨 Adding icon..."
    ICON_DIR="$APP_NAME.app/Contents/Resources"
    if [ -d "$ICON_DIR" ]; then
        cp assets/app_icon.icns "$ICON_DIR/applet.icns" 2>/dev/null && echo "   ✓ Icon added"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Success! Created: $APP_NAME.app"
echo ""
echo "📌 How to use:"
echo "   1. Drag '$APP_NAME.app' to your Dock"
echo "   2. Click to start"
echo "   3. Terminal will open and start the app"
echo "   4. Terminal closes when you quit the app"
echo ""
echo "✨ Features:"
echo "   • No permission issues"
echo "   • Auto-updates from git"
echo "   • Works reliably on macOS"
echo ""
