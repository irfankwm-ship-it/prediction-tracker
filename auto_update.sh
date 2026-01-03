#!/bin/bash
# Auto-update prediction tracker on GitHub
# Called by the daily pipeline after predictions are synced

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load GitHub token from env file if exists
if [ -f "$SCRIPT_DIR/.gh_token" ]; then
    source "$SCRIPT_DIR/.gh_token"
fi

# Check if there are changes
if git diff --quiet predictions.json 2>/dev/null && git diff --quiet index.html 2>/dev/null; then
    echo "[$(date)] No changes to push"
    exit 0
fi

# Stage changes
git add predictions.json index.html crowd_votes.json 2>/dev/null || true
git add predictions.json index.html 2>/dev/null || true

# Commit with date
DATE=$(date +%Y-%m-%d)
git commit -m "Update predictions - $DATE

Automated sync from Canadian Intel Hub pipeline.

🤖 Generated with [Claude Code](https://claude.com/claude-code)" || {
    echo "[$(date)] Nothing to commit"
    exit 0
}

# Push to GitHub
if [ -n "$GH_TOKEN" ]; then
    git remote set-url origin "https://irfankwm-ship-it:${GH_TOKEN}@github.com/irfankwm-ship-it/prediction-tracker.git"
    git push origin main
    git remote set-url origin "https://github.com/irfankwm-ship-it/prediction-tracker.git"
    echo "[$(date)] Pushed to GitHub successfully"
else
    echo "[$(date)] GH_TOKEN not set. Run: echo 'export GH_TOKEN=ghp_yourtoken' > .gh_token"
    exit 1
fi
