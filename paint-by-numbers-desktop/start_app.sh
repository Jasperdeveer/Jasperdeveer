#!/bin/bash

# JSPR Beamer Setup Launcher
# Dit script start de applicatie automatisch met de juiste omgeving

# Ga naar de app directory
cd "$(dirname "$0")"

# Activeer virtual environment
source venv/bin/activate

# Start de applicatie
python main.py

# Deactiveer virtual environment bij afsluiten
deactivate
