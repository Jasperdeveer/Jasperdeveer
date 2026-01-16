#!/bin/bash

# JSPR Beamer Setup Launcher
# Dit script start de applicatie automatisch met de juiste omgeving

# Debug logging
LOG_FILE="/tmp/jspr_app_launcher.log"
echo "=== JSPR App Launcher Log ===" > "$LOG_FILE"
echo "Started at: $(date)" >> "$LOG_FILE"

# Ga naar de app directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
echo "Working directory: $(pwd)" >> "$LOG_FILE"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: venv not found" >> "$LOG_FILE"
    osascript -e 'display dialog "Virtual environment niet gevonden!\n\nOpen Terminal en voer uit:\ncd '"$(pwd)"'\npython3 -m venv venv\nsource venv/bin/activate\npip install -r requirements.txt" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

echo "venv found" >> "$LOG_FILE"

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found" >> "$LOG_FILE"
    osascript -e 'display dialog "main.py niet gevonden in:\n'"$(pwd)"'" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

echo "main.py found" >> "$LOG_FILE"

# Use direct Python path to avoid venv activation issues
PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
echo "Using Python: $PYTHON_BIN" >> "$LOG_FILE"

# Check if Python binary exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "ERROR: Python binary not found at $PYTHON_BIN" >> "$LOG_FILE"
    osascript -e 'display dialog "Python niet gevonden in venv!\n\nHerinstalleer virtual environment:\ncd '"$(pwd)"'\nrm -rf venv\npython3 -m venv venv\nsource venv/bin/activate\npip install -r requirements.txt" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

echo "Python binary found" >> "$LOG_FILE"

# Get Python version
PYTHON_VERSION=$("$PYTHON_BIN" --version 2>&1)
echo "Python version: $PYTHON_VERSION" >> "$LOG_FILE"

# Start the application with splash screen
echo "Starting main_splash.py..." >> "$LOG_FILE"
"$PYTHON_BIN" main_splash.py >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

echo "Exit code: $EXIT_CODE" >> "$LOG_FILE"
echo "Ended at: $(date)" >> "$LOG_FILE"

# Show error dialog if app crashed
if [ $EXIT_CODE -ne 0 ]; then
    osascript -e 'display dialog "App gestopt met error (code '"$EXIT_CODE"').\n\nCheck log:\n/tmp/jspr_app_launcher.log\n\nOf test via Terminal:\ncd '"$(pwd)"'\n./start_app.sh" buttons {"OK"} default button "OK" with icon stop'
fi

exit $EXIT_CODE
