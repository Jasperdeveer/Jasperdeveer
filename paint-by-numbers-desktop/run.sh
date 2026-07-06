#!/bin/bash

# Development launcher for JSPR Beamer Setup
# Use this for quick testing without building the full .app

set -e

echo "🎨 JSPR Beamer Setup - Development Mode"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found."
    echo "Run './build.sh' first to set up the environment."
    echo ""
    read -p "Create virtual environment now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        exit 1
    fi
fi

# Check if dependencies are installed
if ! python -c "import PyQt5" 2>/dev/null; then
    echo "⚠️  Dependencies not installed."
    echo "Installing now..."
    pip install -r requirements.txt
fi

echo "✓ Environment ready"
echo ""

# Run the app
echo "🚀 Starting JSPR Beamer Setup..."
python main.py
