#!/bin/bash

# JSPR Beamer Setup - Simpele werkende launcher voor Dock
# Doet exact hetzelfde als het handmatige commando

# Log naar file voor debugging
LOG_FILE="$HOME/jspr_launcher.log"
exec > "$LOG_FILE" 2>&1

echo "=== JSPR Launcher Start ==="
echo "Time: $(date)"
echo ""

# Zoek de project directory (3 levels omhoog vanaf Contents/MacOS/)
cd "$(dirname "$0")/../../.."
PROJECT_DIR="$(pwd)"

echo "Project dir: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Check of we in de juiste directory zitten
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found in $PROJECT_DIR"
    osascript -e 'display dialog "Fout: main.py niet gevonden!\n\nDirectory: '"$PROJECT_DIR"'\n\nLog: '"$LOG_FILE"'" buttons {"OK"} with icon stop' &
    exit 1
fi

echo "✓ main.py found"

# Check venv
if [ ! -d "venv" ]; then
    echo "ERROR: venv not found"
    osascript -e 'display dialog "Virtual environment niet gevonden!\n\nRun: ./install.sh\n\nLog: '"$LOG_FILE"'" buttons {"OK"} with icon stop' &
    exit 1
fi

echo "✓ venv found"

# Git pull (stil, geen error als het mislukt)
echo ""
echo "Updating from git..."
git pull origin claude/enhance-line-drawing-precision-kyhzU 2>&1 || echo "Git pull failed (continuing anyway)"

# Activeer venv
echo ""
echo "Activating venv..."
source venv/bin/activate

# Check python
echo "Python: $(which python)"
echo "Version: $(python --version 2>&1)"

# Start de app
echo ""
echo "Starting main.py..."
echo ""

python main.py

EXIT_CODE=$?
echo ""
echo "=== App Stopped ==="
echo "Exit code: $EXIT_CODE"
echo "Time: $(date)"

if [ $EXIT_CODE -ne 0 ]; then
    osascript -e 'display dialog "App crashed!\n\nExit code: '"$EXIT_CODE"'\n\nLog: '"$LOG_FILE"'" buttons {"OK"} with icon stop' &
fi

exit $EXIT_CODE
