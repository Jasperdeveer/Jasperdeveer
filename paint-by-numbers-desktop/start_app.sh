#!/bin/bash

# JSPR Beamer Setup Launcher
# Dit script start de applicatie automatisch met de juiste omgeving

# Ga naar de app directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    osascript -e 'display dialog "Virtual environment niet gevonden!\n\nOpen Terminal en voer uit:\ncd '"$(pwd)"'\npython3 -m venv venv\nsource venv/bin/activate\npip install -r requirements.txt" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    osascript -e 'display dialog "main.py niet gevonden in:\n'"$(pwd)"'" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Use direct Python path to avoid venv activation issues
PYTHON_BIN="$(pwd)/venv/bin/python"

# Start the application
"$PYTHON_BIN" main.py
