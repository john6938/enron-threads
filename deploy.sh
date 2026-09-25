#!/usr/bin/env bash
# Deploy web/ to the gh-pages branch as a single force-pushed orphan commit.
# Run after the data pipeline has generated web/data/threads-*.json.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
REMOTE_URL="$(git -C "$REPO_ROOT" remote get-url origin)"

# Ensure npm dependencies are available
if [ ! -d "$REPO_ROOT/node_modules" ]; then
    echo "node_modules not found — run: npm install" >&2
    exit 1
fi

echo "Copying CSS/JS assets into web/..."
cd "$REPO_ROOT"
npx grunt copy --quiet

# Rebuild users.txt from whatever JSON files are present
echo "Rebuilding users.txt..."
ls web/data/threads-*.json 2>/dev/null \
    | sed 's|.*/web/data/||' > web/data/users.txt
USER_COUNT="$(wc -l < web/data/users.txt)"
echo "  ${USER_COUNT} user mailboxes"

# Stage the deploy in a temp dir (exclude pipeline intermediates)
WORK="$(mktemp -d)"
trap "rm -rf '$WORK'" EXIT

echo "Staging web/ for deployment..."
rsync -a \
    --exclude='addresses.tsv' \
    --exclude='data_perl' \
    "$REPO_ROOT/web/" "$WORK/"

# Create a single orphan commit and force-push
cd "$WORK"
git init
git symbolic-ref HEAD refs/heads/gh-pages
git add -A
git commit -m "Deploy $(date -u '+%Y-%m-%d %H:%M UTC') — ${USER_COUNT} mailboxes"
git push --force "$REMOTE_URL" HEAD:gh-pages

echo ""
echo "Done. GitHub Pages will update within ~30 seconds."
echo "One-time setup (if not done): repo Settings → Pages → Branch: gh-pages, folder: /"
