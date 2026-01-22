#!/bin/bash
# Run DEVELOPMENT version of JSPR Beamer Setup
# This runs the latest features (may be unstable!)

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔧 Starting JSPR Beamer Setup (DEVELOPMENT version)"
echo "================================================"
echo "⚠️  Warning: This is the development version with untested features!"
echo ""

# Ensure we're on dev branch
echo "📌 Switching to dev branch..."
git checkout dev 2>/dev/null || {
    echo "⚠️  Warning: Could not switch to dev branch (may already be there)"
}

# Activate virtual environment
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Error: Virtual environment not found!"
    echo "Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import PyQt5" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the application
echo "🚀 Launching application..."
echo ""
cd src && python3 main_window.py

# Deactivate venv on exit
deactivate
