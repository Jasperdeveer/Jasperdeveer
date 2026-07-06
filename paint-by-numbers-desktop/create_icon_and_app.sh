#!/bin/bash

# Script om automatisch een icoon te maken en de .app te bouwen
# Voor JSPR Beamer Setup

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎨 JSPR Beamer Setup - Icoon & App Maker"
echo "========================================"
echo ""

# Stap 1: Maak icoon met Python
echo "📦 Stap 1: Icoon genereren..."
if [ -f "generate_icon.py" ]; then
    python3 generate_icon.py
    if [ $? -eq 0 ]; then
        echo "✅ Icoon gegenereerd"
    else
        echo "⚠️  Icoon genereren mislukt, maar ga door..."
    fi
else
    echo "⚠️  generate_icon.py niet gevonden, icoon overslaan"
fi

echo ""

# Stap 2: Maak .app bundle
echo "📱 Stap 2: .app bundle maken..."

APP_NAME="JSPR Beamer Setup"
APP_PATH="$APP_NAME.app"

# Verwijder oude app
if [ -d "$APP_PATH" ]; then
    rm -rf "$APP_PATH"
fi

# Maak app structuur
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Maak Info.plist
cat > "$APP_PATH/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.jspr.beamersetup</string>
    <key>CFBundleName</key>
    <string>JSPR Beamer Setup</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Maak launcher script
cat > "$APP_PATH/Contents/MacOS/launcher" << 'EOF'
#!/bin/bash

# Zoek de app directory
APP_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$APP_DIR"

# Update naar nieuwste versie
git fetch origin >/dev/null 2>&1
git checkout claude/enhance-line-drawing-precision-kyhzU >/dev/null 2>&1
git pull origin claude/enhance-line-drawing-precision-kyhzU >/dev/null 2>&1

# Activeer venv en start
if [ -d "venv" ]; then
    source venv/bin/activate
    python main.py
else
    osascript -e 'display dialog "Virtual environment niet gevonden!\n\nInstalleer eerst met:\n./install.sh" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi
EOF

chmod +x "$APP_PATH/Contents/MacOS/launcher"

# Kopieer icoon
ICON_FOUND=false

# Probeer verschillende locaties
if [ -f "app_icon.icns" ]; then
    cp "app_icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    ICON_FOUND=true
elif [ -f "assets/app_icon.icns" ]; then
    cp "assets/app_icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    ICON_FOUND=true
elif [ -f "icon.icns" ]; then
    cp "icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    ICON_FOUND=true
elif [ -f "assets/icon.icns" ]; then
    cp "assets/icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    ICON_FOUND=true
fi

echo ""
echo "========================================"
echo "✅ $APP_NAME.app aangemaakt!"
echo ""

if [ "$ICON_FOUND" = true ]; then
    echo "✅ Icoon toegevoegd"
    echo ""
    echo "🔄 Om het icoon te zien:"
    echo "   1. Sleep de .app uit de map en weer terug"
    echo "   2. Of hernoem de .app tijdelijk"
    echo "   3. macOS zal het icoon dan laden"
else
    echo "⚠️  Geen icoon gevonden"
    echo ""
    echo "💡 Tip: Run eerst generate_icon.py om een icoon te maken"
fi

echo ""
echo "📌 Sleep nu '$APP_PATH' naar je Dock!"
echo ""
