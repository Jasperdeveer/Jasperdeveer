#!/bin/bash

# JSPR Beamer Setup - Dubbelklik Launcher
# Automatisch starten met de nieuwste versie

# Ga naar de app directory (waar dit script staat)
cd "$(dirname "$0")"

echo "🚀 JSPR Beamer Setup wordt gestart..."
echo ""

# Check of we op de juiste branch zitten en pull de nieuwste versie
echo "📥 Ophalen nieuwste versie..."
git fetch origin
git checkout claude/enhance-line-drawing-precision-kyhzU
git pull origin claude/enhance-line-drawing-precision-kyhzU

echo ""
echo "✅ Code bijgewerkt naar nieuwste versie"
echo ""

# Activeer virtual environment
if [ -d "venv" ]; then
    echo "🔧 Activeren virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment niet gevonden!"
    echo "   Installeer eerst met: ./install.sh"
    read -p "Druk op Enter om te sluiten..."
    exit 1
fi

# Start de app
echo "✨ Starten JSPR Beamer Setup..."
echo ""
python main.py

# Houd terminal open als er een error is
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ App gestopt met een error"
    read -p "Druk op Enter om te sluiten..."
fi
