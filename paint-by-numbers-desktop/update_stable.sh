#!/bin/bash
# Update STABLE version from remote repository
# Only updates the stable branch (safe!)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📥 Updating STABLE version..."
echo "============================="

# Stash any local changes
if ! git diff-index --quiet HEAD --; then
    echo "💾 Stashing local changes..."
    git stash
    STASHED=true
fi

# Switch to stable and pull
echo "📌 Switching to stable branch..."
git checkout stable

echo "⬇️  Pulling latest stable version..."
timeout 10 git pull origin stable || {
    echo "⚠️  Could not pull from origin (offline or timeout - using local stable)"
}

# Restore stashed changes if any
if [ "$STASHED" = true ]; then
    echo "📤 Restoring local changes..."
    git stash pop
fi

echo ""
echo "✅ Stable version updated!"
echo "Run ./run_stable.sh to start the application"
