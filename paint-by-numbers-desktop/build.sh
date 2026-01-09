#!/bin/bash

# Build script for JSPR Beamer Setup macOS app
# This script automates the process of building a standalone .app bundle

set -e  # Exit on error

echo "🚀 JSPR Beamer Setup - Build Script"
echo "===================================="
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This script must be run on macOS"
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 detected: $(python3 --version)"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install py2app if not installed
if ! pip list | grep -q py2app; then
    echo "📦 Installing py2app..."
    pip install py2app
fi

echo "✓ All dependencies installed"
echo ""

# Clean previous builds
if [ -d "build" ]; then
    echo "🧹 Cleaning previous build..."
    rm -rf build
fi

if [ -d "dist" ]; then
    echo "🧹 Cleaning previous dist..."
    rm -rf dist
fi

echo "✓ Clean complete"
echo ""

# Build the app
echo "🔨 Building JSPR Beamer Setup.app..."
echo "This may take a few minutes..."
python setup.py py2app

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "📦 Your app is located at:"
    echo "   $(pwd)/dist/JSPR Beamer Setup.app"
    echo ""
    echo "You can now:"
    echo "  1. Open it by double-clicking"
    echo "  2. Move it to /Applications"
    echo "  3. Create a DMG for distribution"
    echo ""

    # Open the dist folder in Finder
    open dist
else
    echo ""
    echo "❌ Build failed!"
    echo "Check the error messages above for details"
    exit 1
fi
