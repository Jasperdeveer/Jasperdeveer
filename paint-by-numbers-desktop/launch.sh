#!/bin/bash

# JSPR Beamer Setup Launcher with Version Selector
# This script shows a GUI to choose between Stable and Development version

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the app directory
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

# Run the version selector GUI
python3 version_launcher.py
