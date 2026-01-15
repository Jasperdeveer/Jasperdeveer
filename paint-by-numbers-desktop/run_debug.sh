#!/bin/bash

# Debug launcher for JSPR Beamer Setup with verbose output

set -e

echo "🎨 JSPR Beamer Setup - Debug Mode"
echo "=================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Check dependencies
echo "📦 Checking dependencies..."
if ! python -c "import PyQt5" 2>/dev/null; then
    echo "⚠️  PyQt5 not found. Installing dependencies..."
    pip install -r requirements.txt
fi

echo "✓ Environment ready"
echo ""
echo "🚀 Starting JSPR Beamer Setup with verbose logging..."
echo ""
echo "If the app doesn't appear:"
echo "  1. Check Terminal for error messages"
echo "  2. Look in your Dock for the Python icon"
echo "  3. Check Mission Control (F3) for the window"
echo "  4. Try clicking on the Python icon in Dock"
echo ""
echo "Starting in 2 seconds..."
sleep 2

# Run with Python unbuffered mode for immediate output
PYTHONUNBUFFERED=1 python main.py

echo ""
echo "App closed."
