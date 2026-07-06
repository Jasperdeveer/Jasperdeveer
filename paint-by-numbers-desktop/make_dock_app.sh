#!/bin/bash

# JSPR Beamer Setup - Maak werkende Dock app
# Simpel en betrouwbaar

echo "🚀 JSPR Beamer Setup - Dock App Maker"
echo "======================================"
echo ""

cd "$(dirname "$0")"

APP_NAME="JSPR Beamer Setup"
APP_PATH="$APP_NAME.app"

# Verwijder oude app
if [ -d "$APP_PATH" ]; then
    echo "🗑️  Removing old app..."
    rm -rf "$APP_PATH"
fi

# Maak app structuur
echo "📦 Creating app structure..."
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Info.plist
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

# Kopieer launcher script
echo "📝 Installing launcher..."
cp dock_launcher_script.sh "$APP_PATH/Contents/MacOS/launcher"
chmod +x "$APP_PATH/Contents/MacOS/launcher"

# Kopieer icoon
echo "🎨 Adding icon..."
if [ -f "app_icon.icns" ]; then
    cp "app_icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    echo "   ✓ Icon added"
elif [ -f "assets/app_icon.icns" ]; then
    cp "assets/app_icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    echo "   ✓ Icon added"
else
    echo "   ⚠️  No icon found (run: python3 generate_icon.py)"
fi

echo ""
echo "======================================"
echo "✅ Done! Created: $APP_PATH"
echo ""
echo "📌 Instructions:"
echo "   1. Drag '$APP_PATH' to your Dock"
echo "   2. Click to launch"
echo ""
echo "📝 Logs will be in: ~/jspr_launcher.log"
echo "   View with: tail -f ~/jspr_launcher.log"
echo ""
