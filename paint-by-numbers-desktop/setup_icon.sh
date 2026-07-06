#!/bin/bash

# JSPR Beamer Setup - Icon Setup Script
# Generates and installs the app icon

cd "$(dirname "$0")"

echo "🎨 JSPR Icon Setup"
echo "=================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment niet gevonden!"
    echo "   Run eerst: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Generate icon
echo "📝 Generating icon..."
./venv/bin/python generate_icon.py

if [ ! -f "app_icon.png" ]; then
    echo "❌ Failed to generate icon"
    exit 1
fi

echo "✓ Icon generated"
echo ""

# Convert to .icns
echo "🔄 Converting to macOS .icns format..."
mkdir -p icon.iconset

sips -z 16 16     app_icon.png --out icon.iconset/icon_16x16.png > /dev/null 2>&1
sips -z 32 32     app_icon.png --out icon.iconset/icon_16x16@2x.png > /dev/null 2>&1
sips -z 32 32     app_icon.png --out icon.iconset/icon_32x32.png > /dev/null 2>&1
sips -z 64 64     app_icon.png --out icon.iconset/icon_32x32@2x.png > /dev/null 2>&1
sips -z 128 128   app_icon.png --out icon.iconset/icon_128x128.png > /dev/null 2>&1
sips -z 256 256   app_icon.png --out icon.iconset/icon_128x128@2x.png > /dev/null 2>&1
sips -z 256 256   app_icon.png --out icon.iconset/icon_256x256.png > /dev/null 2>&1
sips -z 512 512   app_icon.png --out icon.iconset/icon_256x256@2x.png > /dev/null 2>&1
sips -z 512 512   app_icon.png --out icon.iconset/icon_512x512.png > /dev/null 2>&1
sips -z 1024 1024 app_icon.png --out icon.iconset/icon_512x512@2x.png > /dev/null 2>&1

iconutil -c icns icon.iconset

if [ ! -f "icon.icns" ]; then
    echo "❌ Failed to convert to .icns"
    exit 1
fi

echo "✓ Converted to .icns"
echo ""

# Install in app bundle
echo "📦 Installing in app bundle..."
mkdir -p "JSPR Beamer Setup.app/Contents/Resources"
cp icon.icns "JSPR Beamer Setup.app/Contents/Resources/icon.icns"

echo "✓ Installed in app bundle"
echo ""

# Cleanup
echo "🧹 Cleaning up..."
rm -rf icon.iconset
echo "✓ Cleanup complete"
echo ""

# Refresh Dock
echo "🔄 Refreshing Dock..."
touch "JSPR Beamer Setup.app"
killall Dock

echo ""
echo "✅ Icon setup complete!"
echo ""
echo "Het icoon zou nu zichtbaar moeten zijn in Finder en je Dock."
echo "Sleep 'JSPR Beamer Setup.app' naar je Dock als je dat nog niet had gedaan."
