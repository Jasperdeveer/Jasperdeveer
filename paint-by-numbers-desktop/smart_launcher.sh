#!/bin/bash

# JSPR Beamer Setup - Smart Launcher
# Shows version selector if possible, otherwise launches stable version

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Setting up JSPR Beamer Setup for first time..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    # Activate virtual environment
    source venv/bin/activate
fi

# Check if we have a display/terminal for the GUI selector
if [ -t 0 ] && [ -n "$DISPLAY" ]; then
    # We have a terminal and display - show version selector
    echo "Starting version selector..."
    python3 version_launcher.py
else
    # No terminal/display - launch stable version directly
    echo "No terminal detected - launching stable version..."

    # Switch to stable branch (silent)
    git checkout stable 2>/dev/null || true

    # Launch main.py
    python3 main.py
fi
