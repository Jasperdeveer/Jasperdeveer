#!/bin/bash

# Script om een macOS .app te maken die in de Dock kan
# Dit maakt een AppleScript applicatie die het .command bestand uitvoert

APP_NAME="JSPR Beamer Setup"
APP_PATH="$APP_NAME.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "📦 Maken van $APP_NAME.app..."

# Verwijder oude app indien aanwezig
if [ -d "$APP_PATH" ]; then
    rm -rf "$APP_PATH"
fi

# Maak app bundle structuur
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

# Zoek de app directory (waar de .app staat)
APP_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$APP_DIR"

# Voer het command bestand uit
if [ -f "Start JSPR Beamer.command" ]; then
    exec "/bin/bash" "Start JSPR Beamer.command"
else
    osascript -e 'display dialog "Start JSPR Beamer.command niet gevonden!" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi
EOF

# Maak launcher executable
chmod +x "$APP_PATH/Contents/MacOS/launcher"

# Kopieer icoon indien aanwezig
if [ -f "assets/icon.icns" ]; then
    cp "assets/icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    echo "✅ Icoon toegevoegd"
elif [ -f "assets/app_icon.icns" ]; then
    cp "assets/app_icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    echo "✅ Icoon toegevoegd"
else
    echo "⚠️  Geen icoon gevonden (optioneel)"
fi

echo ""
echo "✅ $APP_NAME.app aangemaakt!"
echo ""
echo "📌 Sleep nu '$APP_PATH' naar je Dock"
echo "   Of dubbelklik om te starten"
echo ""
