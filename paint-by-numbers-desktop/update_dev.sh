#!/bin/bash
# Update DEVELOPMENT version with latest features
# Pulls latest changes from dev branch

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📥 Updating DEVELOPMENT version..."
echo "=================================="

# Stash any local changes
if ! git diff-index --quiet HEAD --; then
    echo "💾 Stashing local changes..."
    git stash
    STASHED=true
fi

# Switch to dev and pull
echo "📌 Switching to dev branch..."
git checkout dev

echo "⬇️  Pulling latest development version..."
timeout 10 git pull origin dev || {
    echo "⚠️  Could not pull from origin (offline or timeout - using local dev)"
}

# Restore stashed changes if any
if [ "$STASHED" = true ]; then
    echo "📤 Restoring local changes..."
    git stash pop
fi

echo ""
echo "✅ Development version updated!"
echo "Run ./run_dev.sh to start the application"
