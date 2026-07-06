#!/bin/bash

# JSPR Beamer Setup - Dubbelklik Launcher
# Automatisch starten met de nieuwste versie

# Ga naar de app directory (waar dit script staat)
cd "$(dirname "$0")"

echo "🚀 JSPR Beamer Setup wordt gestart..."
echo ""

# Check of we op de juiste branch zitten en pull de nieuwste versie (met timeout)
echo "📥 Ophalen nieuwste versie..."
timeout 3 git fetch origin 2>/dev/null || echo "(Offline - using local version)"
git checkout claude/enhance-line-drawing-precision-kyhzU 2>/dev/null || true
timeout 5 git pull origin claude/enhance-line-drawing-precision-kyhzU 2>/dev/null || echo "(Offline - using local version)"

echo ""
echo "✅ Code klaar"
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

# Start de version selector (die dan de app start)
echo "✨ Starten Version Selector..."
echo ""
python version_launcher.py

# Houd terminal open als er een error is
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ App gestopt met een error"
    read -p "Druk op Enter om te sluiten..."
fi
