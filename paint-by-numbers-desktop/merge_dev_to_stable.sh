#!/bin/bash
# Merge tested features from DEV to STABLE
# ⚠️  Only run this when dev features are fully tested!

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔀 Merging DEV → STABLE"
echo "======================"
echo ""
echo "⚠️  WARNING: This will add new features to the stable version!"
echo "   Only continue if dev has been thoroughly tested."
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Merge cancelled"
    exit 0
fi

# Ensure clean working directory
if ! git diff-index --quiet HEAD --; then
    echo "❌ Error: You have uncommitted changes!"
    echo "   Commit or stash them first"
    exit 1
fi

# Switch to stable
echo "📌 Switching to stable branch..."
git checkout stable

# Merge dev into stable
echo "🔀 Merging dev into stable..."
if git merge dev --no-ff -m "Merge dev → stable: tested features"; then
    echo ""
    echo "✅ Merge successful!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Test the merged version: ./run_stable.sh"
    echo "   2. If everything works: git push origin stable"
    echo "   3. If there are issues: git reset --hard HEAD~1"
else
    echo ""
    echo "❌ Merge conflict! Resolve conflicts and then:"
    echo "   git commit"
    echo "   Or abort: git merge --abort"
    exit 1
fi
