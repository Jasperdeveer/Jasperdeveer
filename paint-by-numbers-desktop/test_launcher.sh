#!/bin/bash

# JSPR Beamer Setup - Test Launcher
# Dit script test of alles werkt voordat de .app wordt gemaakt

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🧪 JSPR Beamer Setup - Launcher Test"
echo "===================================="
echo ""
echo "📂 Working directory: $(pwd)"
echo ""

# Check git
echo "🔍 Checking git status..."
git status --short

echo ""
echo "📥 Updating to latest version..."
git fetch origin
git checkout claude/enhance-line-drawing-precision-kyhzU
git pull origin claude/enhance-line-drawing-precision-kyhzU

echo ""
echo "🔍 Checking files..."
if [ -f "main.py" ]; then
    echo "✅ main.py found"
else
    echo "❌ main.py NOT found"
    exit 1
fi

if [ -d "venv" ]; then
    echo "✅ venv found"
else
    echo "❌ venv NOT found"
    exit 1
fi

echo ""
echo "🐍 Python info..."
source venv/bin/activate
which python
python --version

echo ""
echo "✨ Starting app..."
echo ""
python main.py

exit_code=$?
echo ""
echo "App exited with code: $exit_code"
exit $exit_code
