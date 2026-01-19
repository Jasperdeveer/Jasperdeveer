#!/bin/bash

# JSPR Beamer Setup - Dock App Builder
# Maakt een .app die werkt vanuit de Dock

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🏗️  JSPR Beamer Setup - Dock App Builder"
echo "========================================"
echo ""

APP_NAME="JSPR Beamer Setup"
APP_PATH="$APP_NAME.app"

# Verwijder oude app
if [ -d "$APP_PATH" ]; then
    echo "🗑️  Removing old app..."
    rm -rf "$APP_PATH"
fi

# Maak app structuur
echo "📦 Creating app bundle..."
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

# Maak launcher script met debug logging
cat > "$APP_PATH/Contents/MacOS/launcher" << 'LAUNCHER_EOF'
#!/bin/bash

# JSPR Beamer Setup - App Launcher
# Met debug logging

# Log file
LOG_FILE="/tmp/jspr_dock_launcher.log"
exec > "$LOG_FILE" 2>&1

echo "=== JSPR Beamer Setup Launcher Log ==="
echo "Started at: $(date)"
echo ""

# Find app directory
LAUNCHER_PATH="$(cd "$(dirname "$0")" && pwd)"
echo "Launcher path: $LAUNCHER_PATH"

APP_DIR="$(cd "$LAUNCHER_PATH/../../.." && pwd)"
echo "App directory: $APP_DIR"
cd "$APP_DIR"
echo "Current directory: $(pwd)"
echo ""

# Update code
echo "📥 Updating code..."
git fetch origin 2>&1
git checkout claude/enhance-line-drawing-precision-kyhzU 2>&1
git pull origin claude/enhance-line-drawing-precision-kyhzU 2>&1
echo ""

# Check files
echo "🔍 Checking files..."
if [ ! -f "main.py" ]; then
    osascript -e 'display dialog "main.py not found in:\n'"$APP_DIR"'\n\nCheck log:\n/tmp/jspr_dock_launcher.log" buttons {"OK"} default button "OK" with icon stop' &
    exit 1
fi
echo "✅ main.py found"

if [ ! -d "venv" ]; then
    osascript -e 'display dialog "venv not found!\n\nRun: ./install.sh\n\nCheck log:\n/tmp/jspr_dock_launcher.log" buttons {"OK"} default button "OK" with icon stop' &
    exit 1
fi
echo "✅ venv found"
echo ""

# Activate venv
echo "🐍 Activating virtual environment..."
source venv/bin/activate
echo "Python: $(which python)"
echo "Python version: $(python --version)"
echo ""

# Start app
echo "✨ Starting JSPR Beamer Setup..."
python main.py

exit_code=$?
echo ""
echo "App exited with code: $exit_code"
echo "Ended at: $(date)"

# Show error if crashed
if [ $exit_code -ne 0 ]; then
    osascript -e 'display dialog "App crashed (exit code '"$exit_code"')!\n\nCheck log:\n/tmp/jspr_dock_launcher.log\n\nOr run from Terminal:\ncd '"$APP_DIR"'\n./test_launcher.sh" buttons {"OK"} default button "OK" with icon stop' &
fi

exit $exit_code
LAUNCHER_EOF

chmod +x "$APP_PATH/Contents/MacOS/launcher"

# Kopieer icoon
echo "🎨 Adding icon..."
ICON_FOUND=false

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
echo "✅ $APP_NAME.app created!"
echo ""

if [ "$ICON_FOUND" = true ]; then
    echo "✅ Icon added"
else
    echo "⚠️  No icon found (run ./generate_icon.py first)"
fi

echo ""
echo "📝 Debug info:"
echo "   • App logs: /tmp/jspr_dock_launcher.log"
echo "   • Test manually: ./test_launcher.sh"
echo ""
echo "📌 Usage:"
echo "   1. Drag '$APP_PATH' to your Dock"
echo "   2. Click to start"
echo "   3. If it doesn't start, check /tmp/jspr_dock_launcher.log"
echo ""
